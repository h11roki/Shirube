import pytest

from app.application.ingest_courses import IngestCourses, IngestReport
from app.application.ports import ListingConflictError
from app.domain.course import CourseSection
from app.domain.syllabus import CourseName, Syllabus
from tests.builders import course_section, syllabus


class FakeTimetable:
    def __init__(self, sections: list[CourseSection]) -> None:
        self._sections = sections

    def sections(self) -> list[CourseSection]:
        return self._sections


class FakeSyllabi:
    def __init__(
        self, by_code: dict[str, Syllabus], conflicting: frozenset[str] = frozenset()
    ) -> None:
        self._by_code = by_code
        self._conflicting = conflicting

    def syllabus(self, code: str) -> Syllabus | None:
        if code in self._conflicting:
            raise ListingConflictError(f"{code} が複数のページに現れます")
        return self._by_code.get(code)


class FakeRepository:
    def __init__(self) -> None:
        self.replaced: list[tuple[int, list[CourseSection], list[Syllabus]]] = []

    def replace(self, year: int, sections: list[CourseSection], syllabi: list[Syllabus]) -> None:
        self.replaced.append((year, sections, syllabi))

    def sections(self, year: int) -> list[CourseSection]:
        return []

    def syllabus(self, year: int, code: str) -> Syllabus | None:
        return None


def test_sections_and_their_syllabi_are_stored_once_per_page() -> None:
    sections = [course_section("10001"), course_section("10002"), course_section("10003")]
    shared = syllabus("10001", aliases=(CourseName("10002", "別名(6T)"),))
    repository = FakeRepository()

    report = IngestCourses(
        FakeTimetable(sections), FakeSyllabi({"10001": shared, "10002": shared}), repository
    ).run(2026)

    assert report == IngestReport(sections=3, syllabi=1, codes_without_syllabus=("10003",))
    assert repository.replaced == [(2026, sections, [shared])]


def test_conflicting_code_counts_as_without_syllabus() -> None:
    sections = [course_section("10001"), course_section("10002")]
    repository = FakeRepository()

    report = IngestCourses(
        FakeTimetable(sections),
        FakeSyllabi({"10001": syllabus("10001")}, conflicting=frozenset({"10002"})),
        repository,
    ).run(2026)

    assert report.codes_without_syllabus == ("10002",)
    assert repository.replaced[0][2] == [syllabus("10001")]


def test_syllabus_of_another_year_is_rejected() -> None:
    ingest = IngestCourses(
        FakeTimetable([course_section("10001")]),
        FakeSyllabi({"10001": syllabus("10001", year=2025)}),
        FakeRepository(),
    )

    with pytest.raises(ValueError, match="年度"):
        ingest.run(2026)
