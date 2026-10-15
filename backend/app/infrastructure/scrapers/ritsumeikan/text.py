import re

from app.domain.syllabus import CourseName

FACULTY_SEPARATOR = ","
NAME_SEPARATOR = "、"
TITLE_SEPARATOR = "§"
COURSE_CODE = re.compile(r"^\d{5}$")


def split_list(text: str, separator: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in text.split(separator) if item.strip())


def split_titles(text: str) -> tuple[CourseName, ...]:
    names = []
    for part in split_list(text, TITLE_SEPARATOR):
        code, _, title = part.partition(":")
        if not COURSE_CODE.match(code):
            raise ValueError(f"科目名に授業コードがありません: {text!r}")
        names.append(CourseName(code, title.strip()))
    if not names:
        raise ValueError(f"科目名がありません: {text!r}")
    return tuple(names)
