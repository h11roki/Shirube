from collections import defaultdict
from collections.abc import Set

from app.application.ports import ChunkSearch, CourseRepository, Embedder
from app.domain.ranking import CourseMatch, rank_courses


class SearchError(ValueError):
    pass


class SearchCourses:
    def __init__(self, courses: CourseRepository, chunks: ChunkSearch, embedder: Embedder) -> None:
        self._courses = courses
        self._chunks = chunks
        self._embedder = embedder

    def candidates(self, year: int, department: str, grades: Set[int]) -> set[str]:
        return {name for names in self._pages(year, department, grades).values() for name in names}

    def run(
        self, year: int, queries: list[str], department: str, grades: Set[int], limit: int
    ) -> list[list[CourseMatch]]:
        names_of_page = self._pages(year, department, grades)
        if not names_of_page or not queries:
            return [[] for _ in queries]
        model = self._embedder.model
        if year in self._chunks.years_not_embedded(model):
            raise SearchError(f"{year} 年度のシラバスがモデル {model} で埋め込まれていません")
        vectors = self._embedder.embed(queries)
        if len(vectors) != len(queries):
            raise SearchError(f"埋め込み {len(vectors)} 件がクエリ {len(queries)} 件と合いません")
        pages = set(names_of_page)
        return [
            rank_courses(self._chunks.best_chunks(year, model, vector, pages), names_of_page, limit)
            for vector in vectors
        ]

    def _pages(self, year: int, department: str, grades: Set[int]) -> dict[str, set[str]]:
        page_of = self._courses.syllabus_codes(year)
        names_of_page: dict[str, set[str]] = defaultdict(set)
        for section in self._courses.sections(year):
            offered = any(section.offered_to(department, grade, year) for grade in grades)
            if offered and section.code in page_of:
                names_of_page[page_of[section.code]].add(section.name)
        return names_of_page
