import re
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass
from datetime import timedelta, timezone
from enum import Enum

COURSE_CODE = re.compile(r"^\d{5}$")
ALL_GRADES = frozenset({1, 2, 3, 4})
UNIVERSITY_TIME = timezone(timedelta(hours=9), "JST")


class Term(Enum):
    SPRING = "spring"
    AUTUMN = "autumn"


class Weekday(Enum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


@dataclass(frozen=True)
class TimeSlot:
    weekday: Weekday
    period: int


@dataclass(frozen=True)
class Audience:
    entry_year_from: int
    entry_year_to: int
    eligible_grades: frozenset[int]
    category: str


@dataclass(frozen=True)
class CourseSection:
    code: str
    name: str
    class_code: str | None
    term: Term | None
    slots: tuple[TimeSlot, ...]
    departments: frozenset[str] | None
    audiences: tuple[Audience, ...]
    credits: int
    instructors: tuple[str, ...]
    room: str | None
    registration: str
    note: str | None

    def for_department(self, department: str) -> bool:
        return self.departments is None or department in self.departments

    def offered_to(self, department: str, grade: int, year: int) -> bool:
        cohort_in_grade = year - grade + 1
        return self.for_department(department) and any(
            grade in audience.eligible_grades
            and audience.entry_year_from <= cohort_in_grade <= audience.entry_year_to
            for audience in self.audiences
        )


def left_out_codes(
    sections: Sequence[CourseSection],
    page_of: Mapping[str, str],
    department: str,
    taken: Set[str],
) -> frozenset[str]:
    taken_pages = {
        page_of[section.code]
        for section in sections
        if section.name in taken and section.code in page_of and section.for_department(department)
    }
    return frozenset(
        section.code
        for section in sections
        if section.name in taken or page_of.get(section.code) in taken_pages
    )
