from dataclasses import replace

import pytest

from app.application.ingest_courses import (
    IngestError,
    IngestSyllabi,
    IngestTimetable,
    SyllabusReport,
)
from app.domain.course import Audience, CourseSection
from app.domain.syllabus import CourseName, Syllabus
from tests.builders import course_section, syllabus


class FakeTimetable:
    def __init__(self, *sections: CourseSection) -> None:
        self._sections = list(sections)

    def sections(self) -> list[CourseSection]:
        return self._sections


class FakeSyllabi:
    def __init__(self, *syllabi: Syllabus) -> None:
        self._syllabi = list(syllabi)

    def syllabus(self, code: str) -> Syllabus | None:
        return next((page for page in self._syllabi if page.code == code), None)

    def syllabi(self) -> list[Syllabus]:
        return self._syllabi


class FakeRepository:
    def __init__(self, *sections: CourseSection) -> None:
        self.stored_sections = list(sections)
        self.section_calls: list[tuple[int, list[CourseSection]]] = []
        self.syllabus_calls: list[tuple[int, list[Syllabus]]] = []

    def replace_sections(self, year: int, sections: list[CourseSection]) -> None:
        self.section_calls.append((year, sections))

    def replace_syllabi(self, year: int, syllabi: list[Syllabus]) -> None:
        self.syllabus_calls.append((year, syllabi))

    def sections(self, year: int) -> list[CourseSection]:
        return self.stored_sections

    def syllabus(self, year: int, code: str) -> Syllabus | None:
        return None


def test_timetables_of_a_year_are_stored_together_without_repeats() -> None:
    shared = course_section("10002")
    repository = FakeRepository()
    sources = [
        FakeTimetable(course_section("10001"), shared),
        FakeTimetable(shared, course_section("10003")),
    ]

    rows = IngestTimetable(sources, repository).run(2026)

    assert rows == 3
    assert repository.section_calls == [
        (2026, [course_section("10001"), shared, course_section("10003")])
    ]


def test_same_code_with_different_rows_is_an_error() -> None:
    sources = [
        FakeTimetable(course_section("10001")),
        FakeTimetable(replace(course_section("10001"), room="F202")),
    ]
    repository = FakeRepository()

    with pytest.raises(IngestError, match="10001"):
        IngestTimetable(sources, repository).run(2026)
    assert repository.section_calls == []


def test_empty_timetable_does_not_wipe_the_year() -> None:
    repository = FakeRepository()

    with pytest.raises(IngestError, match="1 件も"):
        IngestTimetable([FakeTimetable()], repository).run(2026)
    assert repository.section_calls == []


def test_timetable_of_another_year_is_rejected() -> None:
    repository = FakeRepository()

    with pytest.raises(IngestError, match="2026 が 2027"):
        IngestTimetable([FakeTimetable(course_section("10001"))], repository).run(2027)
    assert repository.section_calls == []


def test_previous_year_timetable_mixed_with_this_year_is_rejected() -> None:
    last_year = replace(
        course_section("20001"),
        audiences=(Audience(2019, 2025, frozenset({1, 2, 3, 4}), "専門"),),
    )
    sources = [FakeTimetable(course_section("10001")), FakeTimetable(last_year)]
    repository = FakeRepository()

    with pytest.raises(IngestError, match="2 つ目の時間割表の最も新しい入学年度 2025"):
        IngestTimetable(sources, repository).run(2026)
    assert repository.section_calls == []


def test_syllabi_are_stored_and_codes_without_a_page_are_reported() -> None:
    shared = syllabus("10001", aliases=(CourseName("10002", "別名(6T)"),))
    repository = FakeRepository(
        course_section("10001"), course_section("10002"), course_section("10003")
    )

    report = IngestSyllabi(FakeSyllabi(shared), repository).run(2026)

    assert report == SyllabusReport(pages=1, codes_without_syllabus=("10003",))
    assert repository.syllabus_calls == [(2026, [shared])]


@pytest.mark.parametrize(
    ("pages", "message"),
    [
        (
            [syllabus("10001", aliases=(CourseName("10002", "別名(6T)"),)), syllabus("10002")],
            "10002 が 2 か所に現れます: ページ 10001 と 10002",
        ),
        (
            [syllabus("10001"), syllabus("10001")],
            "10001 が 2 か所に現れます: ページ 10001 と 10001",
        ),
        (
            [syllabus("10001", aliases=(CourseName("10002", "甲"), CourseName("10002", "乙")))],
            "10002 が 2 か所に現れます: ページ 10001 と 10001",
        ),
    ],
    ids=["alias-on-another-page", "same-page-saved-twice", "alias-repeated-on-a-page"],
)
def test_code_appearing_twice_is_an_error(pages: list[Syllabus], message: str) -> None:
    repository = FakeRepository()

    with pytest.raises(IngestError, match=message):
        IngestSyllabi(FakeSyllabi(*pages), repository).run(2026)
    assert repository.syllabus_calls == []


def test_no_saved_syllabi_does_not_wipe_the_year() -> None:
    repository = FakeRepository()

    with pytest.raises(IngestError, match="ありません"):
        IngestSyllabi(FakeSyllabi(), repository).run(2026)
    assert repository.syllabus_calls == []


def test_syllabus_of_another_year_is_rejected() -> None:
    repository = FakeRepository()

    with pytest.raises(IngestError, match="年度 2025"):
        IngestSyllabi(FakeSyllabi(syllabus("10001", year=2025)), repository).run(2026)
    assert repository.syllabus_calls == []
