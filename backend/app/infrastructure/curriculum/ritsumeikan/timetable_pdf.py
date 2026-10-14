import re
import unicodedata
from pathlib import Path

import pdfplumber

from app.domain.course import Audience, CourseSection, Term, TimeSlot, Weekday

COLUMN_COUNT = 13
TERM_BY_SECTION = {"春学期": Term.SPRING, "秋学期": Term.AUTUMN}
WEEKDAY_BY_KANJI = {
    "月": Weekday.MON,
    "火": Weekday.TUE,
    "水": Weekday.WED,
    "木": Weekday.THU,
    "金": Weekday.FRI,
    "土": Weekday.SAT,
    "日": Weekday.SUN,
}
ALL_DEPARTMENTS = "全"
MAX_GRADE = 4
NOTE_MARK = "※"
VARIANT_SEPARATOR = "/"
NAME_SEPARATOR = "、"
DEPARTMENT_SEPARATOR = "・"
EMPTY_ROOM = "-"
CARRIED_LINE_MARK = re.compile(r"^I ?", re.MULTILINE)
SECTION_HEADING = re.compile(r"^【(.+?)】")
COURSE_CODE = re.compile(r"^\d{5}$")
PERIOD_RANGE = re.compile(r"(\d+)-(\d+)")
ENTRY_YEARS = re.compile(r"^(\d{2})(?:-(\d{2}))?$")
GRADES = re.compile(r"^(\d(?:[～~]\d)?(?:\.\d(?:[～~]\d)?)*)(のみ)?$")
GRADE_RANGE = re.compile(r"^(\d)[～~](\d)$")
WHITESPACE = re.compile(r"\s+")
RADICAL_CHARS = frozenset(map(chr, range(0x2E80, 0x2FE0)))


def parse_timetable(path: Path) -> list[CourseSection]:
    sections: list[CourseSection] = []
    term: Term | None = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for raw_row in table:
                    row = [_unified(cell or "") for cell in raw_row]
                    heading = SECTION_HEADING.match(row[0])
                    if heading:
                        term = TERM_BY_SECTION.get(heading.group(1))
                        continue
                    if len(row) != COLUMN_COUNT:
                        continue
                    cells = normalize_row(row)
                    if COURSE_CODE.match(_compact(cells[6])):
                        sections.append(section_from_row(term, cells))
    return sections


def normalize_row(row: list[str]) -> list[str]:
    if not row[0].startswith("I"):
        return row
    return [CARRIED_LINE_MARK.sub("", cell) for cell in row]


def section_from_row(term: Term | None, cells: list[str]) -> CourseSection:
    (
        weekday,
        period,
        category,
        departments,
        entry_years,
        grades,
        code,
        name,
        class_code,
        credits,
        instructors,
        room,
        registration,
    ) = cells
    title, _, note = _joined(name).partition(NOTE_MARK)
    return CourseSection(
        code=_compact(code),
        name=title.strip(),
        class_code=_last_line(class_code) or None,
        term=term,
        slots=_slots(_compact(weekday), _compact(period)),
        departments=_departments(_compact(departments)),
        audiences=_audiences(_compact(category), _compact(entry_years), _compact(grades)),
        credits=int(_compact(credits)),
        instructors=tuple(_names(instructors)),
        room=_room(room),
        registration=_compact(registration),
        note=note.strip() or None,
    )


def _slots(weekday: str, period: str) -> tuple[TimeSlot, ...]:
    day = WEEKDAY_BY_KANJI.get(weekday)
    span = PERIOD_RANGE.search(period)
    if day is None or span is None:
        return ()
    first, last = int(span.group(1)), int(span.group(2))
    return tuple(TimeSlot(day, (start + 1) // 2) for start in range(first, last + 1, 2))


def _departments(text: str) -> frozenset[str] | None:
    if text == ALL_DEPARTMENTS:
        return None
    return frozenset(text.split(DEPARTMENT_SEPARATOR))


def _audiences(category: str, entry_years: str, grades: str) -> tuple[Audience, ...]:
    columns = [text.split(VARIANT_SEPARATOR) for text in (category, entry_years, grades)]
    count = max(len(column) for column in columns)
    aligned = [column if len(column) == count else column * count for column in columns]
    return tuple(
        Audience(*_year_range(years), eligible_grades=_grades(grade), category=cat)
        for cat, years, grade in zip(*aligned, strict=True)
    )


def _year_range(text: str) -> tuple[int, int]:
    matched = ENTRY_YEARS.match(text)
    if matched is None:
        raise ValueError(f"入学年度を読めません: {text!r}")
    first = 2000 + int(matched.group(1))
    second = 2000 + int(matched.group(2)) if matched.group(2) else first
    return min(first, second), max(first, second)


def _grades(text: str) -> frozenset[int]:
    matched = GRADES.match(text)
    if matched is None:
        raise ValueError(f"回生を読めません: {text!r}")
    listed = frozenset(grade for part in matched.group(1).split(".") for grade in _grade_part(part))
    if matched.group(2):
        return listed
    return frozenset(range(min(listed), MAX_GRADE + 1))


def _grade_part(text: str) -> range:
    span = GRADE_RANGE.match(text)
    if span is None:
        return range(int(text), int(text) + 1)
    return range(int(span.group(1)), int(span.group(2)) + 1)


def _names(text: str) -> list[str]:
    return [name.strip() for name in _joined(text).split(NAME_SEPARATOR) if name.strip()]


def _last_line(text: str) -> str:
    lines = [_compact(line) for line in text.splitlines() if _compact(line)]
    return lines[-1] if lines else ""


def _room(text: str) -> str | None:
    joined = _joined(text).strip()
    return None if joined in ("", EMPTY_ROOM) else joined


def _unified(text: str) -> str:
    return "".join(
        unicodedata.normalize("NFKC", char) if char in RADICAL_CHARS else char for char in text
    )


def _joined(text: str) -> str:
    return text.replace("\n", "")


def _compact(text: str) -> str:
    return WHITESPACE.sub("", text)
