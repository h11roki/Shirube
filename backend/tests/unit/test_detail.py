from pathlib import Path

import pytest

from app.domain.syllabus import GradingItem
from app.infrastructure.scrapers.ritsumeikan.detail import SyllabusFormatError, parse_detail

FIXTURES = Path(__file__).parents[1] / "fixtures" / "html" / "ritsumeikan"


def fixture(code: str) -> str:
    return (FIXTURES / f"detail_{code}.html").read_text(encoding="utf-8")


def test_header_fields_are_read_from_the_summary_table() -> None:
    syllabus = parse_detail(fixture("32463"))

    assert syllabus.code == "32463"
    assert syllabus.title == "32463:電子情報工学入門(6A)"
    assert syllabus.year == 2026
    assert syllabus.term_label == "春セメスター"
    assert syllabus.slot_label == "月5"
    assert syllabus.faculties == ("理工学部",)
    assert syllabus.instructors == ("AHMAD A. AMINUDDIN", "三木 信彦", "孟 林")
    assert syllabus.credits == 2
    assert syllabus.campus == "BKC"
    assert syllabus.language == "日本語"


def test_text_fields_keep_line_breaks() -> None:
    syllabus = parse_detail(fixture("32463"))

    assert syllabus.overview.startswith("電子情報工学科の勉学研究内容について概説し")
    assert "\n(1) 電子情報工学科に関連するテーマの学習とプレゼンテーション" in syllabus.overview
    assert syllabus.objectives.startswith(
        "(1) 電子情報工学科での勉学研究の内容の概要を理解している。"
    )
    assert syllabus.preparation == "なし"
    assert syllabus.class_format == "対面実施します。"
    assert syllabus.self_study.startswith("テキストの予習・復習")
    assert syllabus.grading_note == ""
    assert syllabus.advice == ""
    assert syllabus.remarks == ""


def test_schedule_and_grading_tables_become_rows() -> None:
    syllabus = parse_detail(fixture("32463"))

    assert len(syllabus.sessions) == 15
    assert syllabus.sessions[0].label == "-"
    assert syllabus.sessions[1].label.startswith("1 /")
    assert syllabus.sessions[1].theme == "電子情報工学科での学び"
    assert syllabus.sessions[1].keywords.startswith("カリキュラム、オンラインシラバス")
    assert syllabus.grading[0] == GradingItem("定期試験（筆記）", "", "")
    assert syllabus.grading[1].percentage == "100"
    assert syllabus.grading[1].kind.startswith("上記以外の試験・レポート")


@pytest.mark.parametrize(
    ("code", "title", "slot", "instructors"),
    [
        ("32469", "32469:電子回路Ⅰ(6T)", "水2", ("白畑 正芳",)),
        ("32494", "32494:電子回路Ⅱ(6T)", "木3", ("田中 亜実",)),
    ],
)
def test_other_courses_parse_consistently(
    code: str, title: str, slot: str, instructors: tuple[str, ...]
) -> None:
    syllabus = parse_detail(fixture(code))

    assert syllabus.code == code
    assert syllabus.title == title
    assert syllabus.slot_label == slot
    assert syllabus.instructors == instructors
    assert syllabus.sessions[0].label == "-"
    assert syllabus.sessions[1].label == "1"
    assert any("～" in session.label or "-" in session.label for session in syllabus.sessions[2:])


def test_page_without_the_summary_table_is_an_error() -> None:
    with pytest.raises(SyllabusFormatError, match="見出し表"):
        parse_detail("<html><body>シラバス情報: 202600001</body></html>")
