from pathlib import Path

import pytest

from app.domain.syllabus import CourseName
from app.infrastructure.scrapers.ritsumeikan.listing import (
    ListingFormatError,
    PageCount,
    parse_listing,
    parse_page_count,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "html" / "ritsumeikan" / "search_results.html"


def test_search_results_page_yields_one_row_per_course() -> None:
    rows = parse_listing(FIXTURE.read_text(encoding="utf-8"))

    assert [row.code for row in rows] == ["32463", "32464", "32465"]
    first = rows[0]
    assert first.title == "電子情報工学入門(6A)"
    assert first.faculties == ("理工学部",)
    assert first.term_label == "春セメスター"
    assert first.slot_label == "月5"
    assert first.campus == "BKC"
    assert first.instructors == ("AHMAD A. AMINUDDIN", "三木 信彦", "孟 林")
    assert first.language == "日本語"
    assert first.credits == "2"
    assert first.href == "/syllabus/s/r-syllabus/a0ifD000003Rw21QAC/202632463"
    assert first.aliases == ()


def test_cross_listed_row_keeps_the_other_names_as_aliases() -> None:
    link = (
        "<th><a href='/syllabus/s/r-syllabus/x/202616806'>"
        "16806:平和人権フィールドスタディ (GR) § 16807:国際平和交流セミナー(GR)</a></th>"
    )
    cells = (
        "<td>理工学部</td><td>通年</td><td></td><td>衣笠</td><td>甲</td><td>日本語</td><td>2</td>"
    )
    html = f"<table><tbody><tr>{link}{cells}</tr></tbody></table>"

    row = parse_listing(html)[0]

    assert row.code == "16806"
    assert row.title == "平和人権フィールドスタディ (GR)"
    assert row.aliases == (CourseName("16807", "国際平和交流セミナー(GR)"),)


def test_row_with_too_few_cells_is_an_error() -> None:
    link = "<th><a href='/syllabus/s/r-syllabus/x/202610001'>10001:a</a></th>"
    html = f"<table><tbody><tr>{link}<td>b</td></tr></tbody></table>"

    with pytest.raises(ListingFormatError, match="一覧の行"):
        parse_listing(html)


def test_alias_without_a_course_code_is_an_error() -> None:
    link = "<th><a href='/syllabus/s/r-syllabus/x/202610001'>10001:a § b</a></th>"
    cells = (
        "<td>理工学部</td><td>通年</td><td></td><td>衣笠</td><td>甲</td><td>日本語</td><td>2</td>"
    )
    html = f"<table><tbody><tr>{link}{cells}</tr></tbody></table>"

    with pytest.raises(ListingFormatError, match="授業コード"):
        parse_listing(html)


def test_page_count_is_read_from_the_summary_text() -> None:
    assert parse_page_count("全 123 件（2 / 3 ページ）") == PageCount(123, 2, 3)


def test_missing_summary_text_means_no_count() -> None:
    assert parse_page_count("該当する科目はありません") is None
