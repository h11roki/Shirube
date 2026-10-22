from pathlib import Path

import pytest

from app.domain.syllabus import CourseName
from app.infrastructure.scrapers.ritsumeikan.listing import (
    ListingFormatError,
    PageCount,
    parse_listing,
    parse_page_count,
)
from tests.unit.listing_page import listing_page

FIXTURE = Path(__file__).parents[1] / "fixtures" / "html" / "ritsumeikan" / "search_results.html"


def test_search_results_page_yields_one_row_per_course() -> None:
    rows = parse_listing(FIXTURE.read_text(encoding="utf-8"))

    assert [row.code for row in rows] == ["10001", "10002", "10003", "10004"]
    first = rows[0]
    assert first.title == "架空工学概論(6A)"
    assert first.faculties == ("理工学部",)
    assert first.term_label == "春セメスター"
    assert first.slot_label == "月5"
    assert first.campus == "BKC"
    assert first.instructors == ("ALEX EXAMPLE", "架空 太郎", "仮名 花子")
    assert first.language == "日本語"
    assert first.credits == "2"
    assert first.href == "/syllabus/s/r-syllabus/a0i000000000001AAA/202610001"
    assert first.aliases == ()
    assert rows[3].title == "架空平和研究 (GR)"
    assert rows[3].aliases == (CourseName("10005", "架空交流演習(GR)"),)


def test_cross_listed_row_keeps_the_other_names_as_aliases() -> None:
    title = "10004:架空平和研究 (GR) § 10005:架空交流演習(GR)"

    row = parse_listing(listing_page((title, "/syllabus/s/r-syllabus/x/202610004")))[0]

    assert row.code == "10004"
    assert row.title == "架空平和研究 (GR)"
    assert row.aliases == (CourseName("10005", "架空交流演習(GR)"),)


def test_row_with_too_few_cells_is_an_error() -> None:
    link = "<th><a href='/syllabus/s/r-syllabus/x/202610001'>10001:a</a></th>"
    html = f"<table><tbody><tr>{link}<td>b</td></tr></tbody></table>"

    with pytest.raises(ListingFormatError, match="一覧の行"):
        parse_listing(html)


@pytest.mark.parametrize(
    "href",
    ["https://other.example/r-syllabus/x/202610001", "@other.example/r-syllabus/x/202610001"],
)
def test_a_link_that_is_not_a_path_on_the_site_is_an_error(href: str) -> None:
    with pytest.raises(ListingFormatError, match="一覧の行"):
        parse_listing(listing_page(("10001:a", href)))


def test_title_without_a_leading_course_code_is_an_error() -> None:
    html = listing_page(("科目 § 10001:a", "/syllabus/s/r-syllabus/x/202610001"))

    with pytest.raises(ListingFormatError, match="授業コード"):
        parse_listing(html)


def test_page_count_is_read_from_the_summary_text() -> None:
    assert parse_page_count("全 123 件（2 / 3 ページ）") == PageCount(123, 2, 3)


def test_missing_summary_text_means_no_count() -> None:
    assert parse_page_count("該当する科目はありません") is None
