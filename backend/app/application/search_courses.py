from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence, Set
from typing import Protocol

from app.application.ports import ChunkSearch, CourseRepository, Embedder, EmbeddingError
from app.domain.course import left_out_codes
from app.domain.ranking import CourseMatch, rank_courses, take_turns
from app.domain.roadmap import Semester, opens_in_any

EXCLUDED_NOTE = "(もう取ったと答えた授業は除いています)"


class SearchError(ValueError):
    pass


class NoCandidatesError(SearchError):
    pass


class SearchTarget(Protocol):
    @property
    def query(self) -> str: ...

    @property
    def skills(self) -> tuple[str, ...]: ...


SearchQueries = Callable[[SearchTarget], list[str]]


def whole_query(target: SearchTarget) -> list[str]:
    return [target.query]


def query_and_skills(target: SearchTarget) -> list[str]:
    return [target.query, *target.skills]


class Candidates:
    def __init__(
        self,
        year: int,
        names_of_page: Mapping[str, Set[str]],
        chunks: ChunkSearch,
        embedder: Embedder,
        queries: SearchQueries,
    ) -> None:
        self._year = year
        self._names_of_page = names_of_page
        self._chunks = chunks
        self._embedder = embedder
        self._queries = queries

    @property
    def names(self) -> set[str]:
        return {name for names in self._names_of_page.values() for name in names}

    def pick(self, targets: Sequence[SearchTarget], limit: int) -> list[list[CourseMatch]]:
        per_target = [self._queries(target) for target in targets]
        texts = list(dict.fromkeys(text for queries in per_target for text in queries))
        vectors = self._embedder.embed(texts)
        if len(vectors) != len(texts):
            raise EmbeddingError(f"埋め込み {len(vectors)} 件がクエリ {len(texts)} 件と合いません")
        pages = set(self._names_of_page)
        ranking_of = {
            text: rank_courses(
                self._chunks.best_chunks(self._year, self._embedder.model, vector, pages),
                self._names_of_page,
                limit,
            )
            for text, vector in zip(texts, vectors, strict=True)
        }
        return [take_turns([ranking_of[text] for text in queries], limit) for queries in per_target]


class SearchCourses:
    def __init__(
        self,
        courses: CourseRepository,
        chunks: ChunkSearch,
        embedder: Embedder,
        queries: SearchQueries,
    ) -> None:
        self._courses = courses
        self._chunks = chunks
        self._embedder = embedder
        self._queries = queries

    def candidates(
        self,
        year: int,
        department: str,
        semesters: Sequence[Semester],
        excluded: Set[str] = frozenset(),
    ) -> Candidates:
        page_of = self._courses.syllabus_codes(year)
        sections = self._courses.sections(year)
        if not page_of or not sections:
            raise SearchError(f"{year} 年度の時間割かシラバスが DB にありません")
        left_out = left_out_codes(sections, page_of, department, excluded)
        names_of_page: dict[str, set[str]] = defaultdict(set)
        removed = False
        for section in sections:
            offered = opens_in_any(section, department, year, semesters)
            if not offered or section.code not in page_of:
                continue
            if section.code in left_out:
                removed = True
                continue
            names_of_page[page_of[section.code]].add(section.name)
        if not names_of_page:
            raise NoCandidatesError(
                f"{year} 年度の {department} に、指定した学期に開講されシラバスのある"
                "候補の科目がありません" + (EXCLUDED_NOTE if removed else "")
            )
        model = self._embedder.model
        if not self._chunks.is_embedded(year, model):
            raise SearchError(f"{year} 年度のシラバスがモデル {model} で埋め込まれていません")
        return Candidates(year, names_of_page, self._chunks, self._embedder, self._queries)
