from collections import defaultdict
from collections.abc import Mapping, Sequence, Set

from app.application.ports import ChunkSearch, CourseRepository, Embedder, EmbeddingError
from app.domain.ranking import CourseMatch, rank_courses
from app.domain.roadmap import Semester, opens_in

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
    ) -> None:
        self._year = year
        self._names_of_page = names_of_page
        self._chunks = chunks
        self._embedder = embedder

    @property
    def names(self) -> set[str]:
        return {name for names in self._names_of_page.values() for name in names}

    def rank(self, queries: list[str], limit: int) -> list[list[CourseMatch]]:
        if not queries:
            return []
        vectors = self._embedder.embed(queries)
        if len(vectors) != len(queries):
            raise EmbeddingError(
                f"埋め込み {len(vectors)} 件がクエリ {len(queries)} 件と合いません"
            )
        pages = set(self._names_of_page)
        return [
            rank_courses(
                self._chunks.best_chunks(self._year, self._embedder.model, vector, pages),
                self._names_of_page,
                limit,
            )
            for vector in vectors
        ]


class SearchCourses:
    def __init__(self, courses: CourseRepository, chunks: ChunkSearch, embedder: Embedder) -> None:
        self._courses = courses
        self._chunks = chunks
        self._embedder = embedder

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
        names_of_page: dict[str, set[str]] = defaultdict(set)
        taken_pages = set()
        for section in sections:
            page = page_of.get(section.code)
            if page is None:
                continue
            in_department = section.departments is None or department in section.departments
            if section.name in excluded and in_department:
                taken_pages.add(page)
            if any(opens_in(section, department, year, semester) for semester in semesters):
                names_of_page[page].add(section.name)
        removed = bool(taken_pages & names_of_page.keys())
        for page in taken_pages:
            names_of_page.pop(page, None)
        if not names_of_page:
            raise NoCandidatesError(
                f"{year} 年度の {department} に、指定した学期に開講されシラバスのある"
                "候補の科目がありません" + (EXCLUDED_NOTE if removed else "")
            )
        model = self._embedder.model
        if not self._chunks.is_embedded(year, model):
            raise SearchError(f"{year} 年度のシラバスがモデル {model} で埋め込まれていません")
        return Candidates(year, names_of_page, self._chunks, self._embedder)
