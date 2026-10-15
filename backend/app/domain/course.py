import re
from dataclasses import dataclass
from enum import Enum

COURSE_CODE = re.compile(r"^\d{5}$")


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
