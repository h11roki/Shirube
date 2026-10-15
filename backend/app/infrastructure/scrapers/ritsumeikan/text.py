import re

from app.domain.course import COURSE_CODE
from app.domain.syllabus import CourseName

FACULTY_SEPARATOR = ","
NAME_SEPARATOR = "、"
TITLE_SEPARATOR = re.compile(r"\s*§\s*(?=\d{5}:)")


def split_list(text: str, separator: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in text.split(separator) if item.strip())


def split_titles(text: str) -> tuple[CourseName, ...]:
    names = []
    for part in TITLE_SEPARATOR.split(text.strip()):
        code, _, title = part.partition(":")
        if not COURSE_CODE.match(code):
            raise ValueError(f"科目名に授業コードがありません: {text!r}")
        names.append(CourseName(code, title.strip()))
    return tuple(names)
