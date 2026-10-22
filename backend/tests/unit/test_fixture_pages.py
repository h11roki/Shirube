from tests.fixtures.html.ritsumeikan.make_pages import (
    DETAIL_PAGES,
    HERE,
    detail_page,
    listing_page,
)


def test_committed_pages_match_the_generator() -> None:
    for page in DETAIL_PAGES:
        saved = (HERE / f"detail_{page.code}.html").read_text(encoding="utf-8")
        assert saved == detail_page(page), page.code
    saved = (HERE / "search_results.html").read_text(encoding="utf-8")
    assert saved == listing_page(DETAIL_PAGES)
