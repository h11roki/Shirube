from dataclasses import replace

from app.application.search_courses import SearchCourses
from app.domain.chunk import ChunkSection
from app.domain.course import ALL_GRADES
from app.domain.ranking import ChunkHit
from app.domain.syllabus import CourseName
from tests.builders import course_section, syllabus
from tests.fakes import FakeCourseRepository

MODEL = "fake-embedding"


class FakeEmbedder:
    model = MODEL

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[1.0, 0.0] for _ in texts]


class FakeChunkSearch:
    def __init__(self, hits: list[ChunkHit]) -> None:
        self._hits = hits
        self.calls: list[tuple[int, str, list[float], set[str]]] = []

    def similarities(
        self, year: int, model: str, vector: list[float], syllabus_codes: set[str]
    ) -> list[ChunkHit]:
        self.calls.append((year, model, vector, syllabus_codes))
        return [hit for hit in self._hits if hit.syllabus_code in syllabus_codes]


def courses() -> FakeCourseRepository:
    return FakeCourseRepository(
        sections=(
            replace(course_section("10001"), name="電子回路Ⅰ"),
            replace(course_section("10002"), name="電子回路Ⅰ"),
            replace(course_section("20001", departments=frozenset({"機"})), name="機械工学"),
            replace(course_section("30001"), name="論理回路"),
            replace(course_section("40001"), name="シラバスの無い科目"),
        ),
        syllabi=(
            syllabus("10001", aliases=(CourseName("10002", "電子回路Ⅰ(6U)"),)),
            syllabus("20001"),
            syllabus("30001"),
        ),
    )


def test_query_is_searched_among_pages_of_courses_open_to_the_student() -> None:
    chunks = FakeChunkSearch(
        [
            ChunkHit("10001", ChunkSection.OVERVIEW, 0.6),
            ChunkHit("20001", ChunkSection.OVERVIEW, 0.9),
            ChunkHit("30001", ChunkSection.SCHEDULE, 0.7),
        ]
    )
    embedder = FakeEmbedder()

    matches = SearchCourses(courses(), chunks, embedder).run(
        2026, "回路の設計", "情", ALL_GRADES, 10
    )

    assert embedder.calls == [["回路の設計"]]
    assert chunks.calls == [(2026, MODEL, [1.0, 0.0], {"10001", "30001"})]
    assert [(match.name, match.similarity) for match in matches] == [
        ("論理回路", 0.7),
        ("電子回路Ⅰ", 0.6),
    ]


def test_candidates_are_course_names_that_have_a_syllabus() -> None:
    search = SearchCourses(courses(), FakeChunkSearch([]), FakeEmbedder())

    assert search.candidates(2026, "情", ALL_GRADES) == {"電子回路Ⅰ", "論理回路"}


def test_no_candidates_means_no_embedding_call() -> None:
    embedder = FakeEmbedder()

    matches = SearchCourses(courses(), FakeChunkSearch([]), embedder).run(
        2026, "回路", "情", frozenset(), 10
    )

    assert matches == []
    assert embedder.calls == []
