import re
from dataclasses import dataclass
from enum import Enum

COURSE_CODE = re.compile(r"^\d{5}$")
ALL_GRADES = frozenset({1, 2, 3, 4})


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

    def offered_to(self, department: str, grade: int, year: int) -> bool:
        cohort_in_grade = year - grade + 1
        in_department = self.departments is None or department in self.departments
        return in_department and any(
            grade in audience.eligible_grades
            and audience.entry_year_from <= cohort_in_grade <= audience.entry_year_to
            for audience in self.audiences
        )
