import re

from bs4 import BeautifulSoup

from app.domain.syllabus import GradingItem, Session, Syllabus
from app.infrastructure.scrapers.ritsumeikan.text import (
    FACULTY_SEPARATOR,
    NAME_SEPARATOR,
    split_list,
)

HEADER_LABELS = (
    "授業科目名",
    "年度",
    "学期",
    "開講曜日・時限",
    "学部・研究科",
    "全担当教員",
    "単位数",
)
TEXT_LABELS = {
    "campus": "キャンパス",
    "language": "授業で利用する言語",
    "overview": "授業の概要と方法",
    "objectives": "受講生の到達目標",
    "preparation": "事前に履修しておくことが望まれる科目",
    "class_format": "授業実施形態",
    "self_study": "授業外学習の指示",
    "grading_note": "成績評価方法(備考)",
    "advice": "受講および研究に関するアドバイス",
    "remarks": "備考",
}
SCHEDULE_LABEL = "授業スケジュール"
GRADING_LABEL = "成績評価方法"
NOTE_ROW_LABEL = "-"
COURSE_CODE = re.compile(r"^\d{5}$")


class SyllabusFormatError(ValueError):
    pass


def parse_detail(html: str) -> Syllabus:
    soup = BeautifulSoup(html, "html.parser")
    header = _header(soup)
    texts = _texts(soup)
    tables = _tables(soup)
    code, _, title = header["授業科目名"].partition(":")
    if not COURSE_CODE.match(code):
        raise SyllabusFormatError(f"科目名に授業コードがありません: {header['授業科目名']!r}")
    try:
        year, credits = int(header["年度"]), int(header["単位数"])
    except ValueError as error:
        raise SyllabusFormatError(
            f"年度か単位数を読めません: {header['年度']!r} {header['単位数']!r}"
        ) from error
    schedule = _rows(tables, SCHEDULE_LABEL, 3)
    return Syllabus(
        code=code,
        title=title,
        year=year,
        term_label=header["学期"],
        slot_label=header["開講曜日・時限"],
        faculties=split_list(header["学部・研究科"], FACULTY_SEPARATOR),
        instructors=split_list(header["全担当教員"], NAME_SEPARATOR),
        credits=credits,
        campus=texts["campus"],
        language=texts["language"],
        overview=texts["overview"],
        objectives=texts["objectives"],
        preparation=texts["preparation"],
        schedule_note="\n".join(theme for label, theme, _ in schedule if label == NOTE_ROW_LABEL),
        sessions=tuple(Session(*row) for row in schedule if row[0] != NOTE_ROW_LABEL),
        class_format=texts["class_format"],
        self_study=texts["self_study"],
        grading=tuple(GradingItem(*row) for row in _rows(tables, GRADING_LABEL, 3)),
        grading_note=texts["grading_note"],
        advice=texts["advice"],
        remarks=texts["remarks"],
    )


def _header(soup: BeautifulSoup) -> dict[str, str]:
    for table in soup.select("table.syllabus-table"):
        labels = [th.get_text(" ", strip=True) for th in table.select("thead th")]
        row = table.select_one("tbody tr")
        if tuple(labels) != HEADER_LABELS or row is None:
            continue
        values = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if len(values) != len(labels):
            raise SyllabusFormatError(f"見出し表の列数が合いません: {values}")
        return dict(zip(labels, values, strict=True))
    raise SyllabusFormatError("科目の見出し表が見つかりません")


def _texts(soup: BeautifulSoup) -> dict[str, str]:
    found: dict[str, str] = {}
    for field in soup.select("div.syllabus-field"):
        label = field.select_one("span.syllabus-field__label")
        value = field.select_one(".syllabus-field__print-text")
        if label is not None and value is not None:
            found[label.get_text(strip=True)] = value.get_text().strip()
    missing = [label for label in TEXT_LABELS.values() if label not in found]
    if missing:
        raise SyllabusFormatError(f"項目が見つかりません: {missing}")
    return {name: found[label] for name, label in TEXT_LABELS.items()}


def _tables(soup: BeautifulSoup) -> dict[str, list[list[str]]]:
    tables: dict[str, list[list[str]]] = {}
    for section in soup.select("section.syllabus-section"):
        label = section.select_one("span.syllabus-section__label-text")
        table = section.select_one("table")
        if label is not None and table is not None:
            tables[label.get_text(strip=True)] = [
                [cell.get_text("\n", strip=True) for cell in tr.find_all(["th", "td"])]
                for tr in table.select("tbody tr")
            ]
    return tables


def _rows(tables: dict[str, list[list[str]]], label: str, width: int) -> list[list[str]]:
    if label not in tables:
        raise SyllabusFormatError(f"表が見つかりません: {label}")
    rows = tables[label]
    if any(len(row) != width for row in rows):
        raise SyllabusFormatError(f"{label} の列数が {width} ではありません")
    return rows
