from collections import defaultdict
from collections.abc import Mapping, Sequence, Set

from app.application.ports import ChunkSearch, CourseRepository, Embedder, EmbeddingError
from app.domain.course import left_out_codes
from app.domain.ranking import CourseMatch, rank_courses, take_turns
from app.domain.roadmap import Semester, opens_in_any

EXCLUDED_NOTE = "(もう取ったと答えた授業は除いています)"


class SearchError(ValueError):
    pass


class NoCandidatesError(SearchError):
    pass


class Candidates:
    def __init__(
        self,
        year: int,
        names_of_page: Mapping[str, Set[str]],
        chunks: ChunkSearch,
        embedder: Embedder,
        by_skill: bool,
    ) -> None:
        self._year = year
        self._names_of_page = names_of_page
        self._chunks = chunks
        self._embedder = embedder
        self._by_skill = by_skill

    @property
    def names(self) -> set[str]:
        return {name for names in self._names_of_page.values() for name in names}

    def pick(self, query: str, skills: Sequence[str], limit: int) -> list[CourseMatch]:
        queries = [query, *skills] if self._by_skill else [query]
        vectors = self._embedder.embed(queries)
        if len(vectors) != len(queries):
            raise EmbeddingError(
                f"埋め込み {len(vectors)} 件がクエリ {len(queries)} 件と合いません"
            )
        pages = set(self._names_of_page)
        rankings = [
            rank_courses(
                self._chunks.best_chunks(self._year, self._embedder.model, vector, pages),
                self._names_of_page,
                limit,
            )
            for vector in vectors
        ]
        return take_turns(rankings, limit)


class SearchCourses:
    def __init__(
        self, courses: CourseRepository, chunks: ChunkSearch, embedder: Embedder, by_skill: bool
    ) -> None:
        self._courses = courses
        self._chunks = chunks
        self._embedder = embedder
        self._by_skill = by_skill

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
        return Candidates(year, names_of_page, self._chunks, self._embedder, self._by_skill)
