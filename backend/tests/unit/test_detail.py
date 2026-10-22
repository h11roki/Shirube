from pathlib import Path

import pytest

from app.domain.syllabus import CourseName, GradingItem
from app.infrastructure.scrapers.ritsumeikan.detail import (
    HEADER_LABELS,
    TEXT_LABELS,
    SyllabusFormatError,
    parse_detail,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "html" / "ritsumeikan"


def fixture(code: str) -> str:
    return (FIXTURES / f"detail_{code}.html").read_text(encoding="utf-8")


def document(
    title: str = "99999:試験科目(A1)", credits: str = "2", dropped_label: str | None = None
) -> str:
    head = "".join(f"<th>{label}</th>" for label in HEADER_LABELS)
    values = [title, "2026", "春セメスター", "月1", "理工学部", "教員 甲、教員 乙", credits]
    body = "".join(f"<td>{value}</td>" for value in values)
    fields = "".join(
        f"<div class='syllabus-field'><span class='syllabus-field__label'>{label}</span>"
        f"<span class='syllabus-field__print-text'>{label}の本文</span></div>"
        for label in TEXT_LABELS.values()
        if label != dropped_label
    )
    schedule = (
        "<tr><td>-</td><td>注記</td><td></td></tr><tr><td>1</td><td>導入</td><td>語</td></tr>"
    )
    grading = "<tr><td>定期試験</td><td>100</td><td>基準</td></tr>"
    sections = "".join(
        f"<section class='syllabus-section'><span class='syllabus-section__label-text'>{label}"
        f"</span><table><tbody>{rows}</tbody></table></section>"
        for label, rows in (("授業スケジュール", schedule), ("成績評価方法", grading))
    )
    return (
        f"<html><body><table class='syllabus-table'><thead><tr>{head}</tr></thead>"
        f"<tbody><tr>{body}</tr></tbody></table>{fields}{sections}</body></html>"
    )


def test_header_fields_are_read_from_the_summary_table() -> None:
    syllabus = parse_detail(fixture("10001"))

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
    entry = parse_detail(fixture("10001"))
    circuits = parse_detail(fixture("10002"))

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
    syllabus = parse_detail(fixture("10001"))

    assert syllabus.schedule_note.startswith("第 1 回はガイダンスを行う。")
    assert len(syllabus.sessions) == 14
    assert syllabus.sessions[0].label.startswith("1 /")
    assert syllabus.sessions[0].theme == "架空工学科での学び"
    assert syllabus.sessions[0].keywords.startswith("カリキュラム、オンラインシラバス")


def test_table_cells_keep_line_breaks() -> None:
    syllabus = parse_detail(fixture("10002"))

    grouped = next(session for session in syllabus.sessions if session.label == "5～7")
    assert "\n" in grouped.keywords


def test_grading_table_becomes_items() -> None:
    syllabus = parse_detail(fixture("10001"))

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
    syllabus = parse_detail(fixture(code))

    assert syllabus.code == code
    assert syllabus.title == title
    assert syllabus.slot_label == slot
    assert syllabus.instructors == instructors
    assert syllabus.sessions[0].label == "1"


def test_synthetic_document_parses_with_note_row_excluded() -> None:
    syllabus = parse_detail(document())

    assert syllabus.code == "99999"
    assert syllabus.title == "試験科目(A1)"
    assert syllabus.instructors == ("教員 甲", "教員 乙")
    assert syllabus.schedule_note == "注記"
    assert [session.theme for session in syllabus.sessions] == ["導入"]
    assert syllabus.grading == (GradingItem("定期試験", "100", "基準"),)


def test_cross_listed_page_keeps_the_other_names_as_aliases() -> None:
    syllabus = parse_detail(fixture("10004"))

    assert syllabus.code == "10004"
    assert syllabus.title == "架空平和研究 (GR)"
    assert syllabus.aliases == (CourseName("10005", "架空交流演習(GR)"),)
    assert syllabus.faculties == ("法学部", "理工学部")


def test_synthetic_cross_listed_title_splits_into_aliases() -> None:
    syllabus = parse_detail(document(title="99999:試験科目(A1) § 99998:別名(A1) § 99997:別名2(B1)"))

    assert syllabus.code == "99999"
    assert syllabus.title == "試験科目(A1)"
    assert syllabus.aliases == (CourseName("99998", "別名(A1)"), CourseName("99997", "別名2(B1)"))


def test_section_sign_inside_a_title_is_not_a_separator() -> None:
    syllabus = parse_detail(document(title="99999:民法入門 §90条(A1) § 99998:別名(A1)"))

    assert syllabus.title == "民法入門 §90条(A1)"
    assert syllabus.aliases == (CourseName("99998", "別名(A1)"),)


def test_unreadable_credits_are_a_format_error() -> None:
    with pytest.raises(SyllabusFormatError, match="単位数"):
        parse_detail(document(credits="2～4"))


def test_title_without_a_course_code_is_a_format_error() -> None:
    with pytest.raises(SyllabusFormatError, match="授業コード"):
        parse_detail(document(title="試験科目(A1)"))


def test_missing_text_field_is_a_format_error() -> None:
    with pytest.raises(SyllabusFormatError, match="項目が見つかりません"):
        parse_detail(document(dropped_label="備考"))


def test_page_without_the_summary_table_is_an_error() -> None:
    with pytest.raises(SyllabusFormatError, match="見出し表"):
        parse_detail("<html><body></body></html>")
