from dataclasses import replace

import pytest

from app.domain.syllabus import CourseName, GradingItem
from app.infrastructure.scrapers.ritsumeikan.detail import SyllabusFormatError, parse_detail
from tests.unit.syllabus_pages import CIRCUITS_1, CROSS_LISTED, INTRODUCTION, PAGES, detail_page

TRIAL = replace(
    INTRODUCTION,
    code="99999",
    title="試験科目(A1)",
    instructors="教員 甲、教員 乙",
    schedule_note="注記",
    sessions=(("1", "導入", "語"),),
    grading=(("定期試験", "100", "基準"),),
)


def test_header_fields_are_read_from_the_summary_table() -> None:
    syllabus = parse_detail(detail_page(INTRODUCTION))

    assert syllabus.code == "10001"
    assert syllabus.title == "架空工学概論(6A)"
    assert syllabus.aliases == ()
    assert syllabus.year == 2026
    assert syllabus.term_label == "春セメスター"
    assert syllabus.slot_label == "月5"
    assert syllabus.faculties == ("理工学部",)
    assert syllabus.instructors == ("ALEX EXAMPLE", "架空 太郎", "仮名 花子")
    assert syllabus.credits == 2
    assert syllabus.campus == "BKC"
    assert syllabus.language == "日本語"


def test_text_fields_keep_line_and_paragraph_breaks() -> None:
    entry = parse_detail(detail_page(INTRODUCTION))
    circuits = parse_detail(detail_page(CIRCUITS_1))

    assert entry.overview.startswith("架空工学科の学びの内容について概説し")
    assert "\n(1) 架空工学科に関連するテーマの学習と発表" in entry.overview
    assert entry.objectives.startswith("(1) 架空工学科での学びの概要を理解している。")
    assert entry.preparation == "なし"
    assert entry.class_format == "対面で実施する。"
    assert entry.self_study.startswith("テキストの予習と復習")
    assert entry.grading_note == ""
    assert entry.advice == ""
    assert entry.remarks == ""
    assert "理解を深める。\n\nさまざまな技術分野" in circuits.overview


def test_schedule_note_is_separated_from_sessions() -> None:
    syllabus = parse_detail(detail_page(INTRODUCTION))

    assert syllabus.schedule_note == "第 1 回はガイダンスを行う。詳細は LMS を参照。"
    assert len(syllabus.sessions) == 14
    assert syllabus.sessions[0].label == "1 / 架空 太郎、ALEX EXAMPLE、仮名  花子"
    assert syllabus.sessions[0].theme == "架空工学科での学び"
    assert syllabus.sessions[0].keywords == "カリキュラム、オンラインシラバス、LMS"


def test_table_cells_keep_line_breaks() -> None:
    syllabus = parse_detail(detail_page(CIRCUITS_1))

    grouped = next(session for session in syllabus.sessions if session.label == "5～7")
    assert grouped.keywords == (
        "小信号の扱いを理解し、トランジスタの等価回路を理解する\n増幅の原理を理解し、各種の接地回路を理解する"
    )


def test_grading_table_becomes_items() -> None:
    syllabus = parse_detail(detail_page(INTRODUCTION))

    assert syllabus.grading[0] == GradingItem("定期試験（筆記）", "", "")
    assert syllabus.grading[1].percentage == "100"
    assert syllabus.grading[1].kind.startswith("上記以外の試験・レポート")


@pytest.mark.parametrize(
    ("code", "title", "slot", "instructors"),
    [
        ("10002", "架空回路Ⅰ(6T)", "水2", ("仮名 一郎",)),
        ("10003", "架空回路Ⅱ(6T)", "木3", ("仮名 二郎",)),
    ],
)
def test_other_courses_parse_consistently(
    code: str, title: str, slot: str, instructors: tuple[str, ...]
) -> None:
    syllabus = parse_detail(detail_page(PAGES[code]))

    assert syllabus.code == code
    assert syllabus.title == title
    assert syllabus.slot_label == slot
    assert syllabus.instructors == instructors
    assert syllabus.sessions[0].label == "1"


def test_note_row_is_excluded_from_sessions() -> None:
    syllabus = parse_detail(detail_page(TRIAL))

    assert syllabus.code == "99999"
    assert syllabus.title == "試験科目(A1)"
    assert syllabus.instructors == ("教員 甲", "教員 乙")
    assert syllabus.schedule_note == "注記"
    assert [session.theme for session in syllabus.sessions] == ["導入"]
    assert syllabus.grading == (GradingItem("定期試験", "100", "基準"),)


def test_cross_listed_page_keeps_the_other_names_as_aliases() -> None:
    syllabus = parse_detail(detail_page(CROSS_LISTED))

    assert syllabus.code == "10004"
    assert syllabus.title == "架空平和研究 (GR)"
    assert syllabus.aliases == (CourseName("10005", "架空交流演習(GR)"),)
    assert syllabus.faculties == ("法学部", "理工学部")


def test_every_other_name_becomes_an_alias() -> None:
    page = replace(TRIAL, aliases=(("99998", "別名(A1)"), ("99997", "別名2(B1)")))

    syllabus = parse_detail(detail_page(page))

    assert syllabus.code == "99999"
    assert syllabus.title == "試験科目(A1)"
    assert syllabus.aliases == (CourseName("99998", "別名(A1)"), CourseName("99997", "別名2(B1)"))


def test_section_sign_inside_a_title_is_not_a_separator() -> None:
    page = replace(TRIAL, title="民法入門 §90条(A1)", aliases=(("99998", "別名(A1)"),))

    syllabus = parse_detail(detail_page(page))

    assert syllabus.title == "民法入門 §90条(A1)"
    assert syllabus.aliases == (CourseName("99998", "別名(A1)"),)


def test_unreadable_credits_are_a_format_error() -> None:
    with pytest.raises(SyllabusFormatError, match="単位数"):
        parse_detail(detail_page(replace(TRIAL, credits="2～4")))


def test_title_without_a_course_code_is_a_format_error() -> None:
    with pytest.raises(SyllabusFormatError, match="授業コード"):
        parse_detail(detail_page(replace(TRIAL, code="")))


def test_missing_text_field_is_a_format_error() -> None:
    with pytest.raises(SyllabusFormatError, match="項目が見つかりません"):
        parse_detail(detail_page(TRIAL, omit="備考"))


def test_page_without_the_summary_table_is_an_error() -> None:
    with pytest.raises(SyllabusFormatError, match="見出し表"):
        parse_detail("<html><body></body></html>")
