from pathlib import Path

import pytest

from app.application.ports import DetailLink, ListingConflictError
from app.infrastructure.scrapers.ritsumeikan.listing import ListingFormatError
from app.infrastructure.scrapers.ritsumeikan.store import RawStore
from tests.unit.syllabus_pages import listing_page

PAGE_X = "/r-syllabus/x/202610001"
PAGE_Y = "/r-syllabus/y/202610002"


def test_same_code_on_the_same_page_in_two_listings_is_one_link(tmp_path: Path) -> None:
    store = RawStore(tmp_path, 2026)
    store.save_listing("a", [listing_page(("10001:甲 § 10002:乙", PAGE_X))])
    store.save_listing("b", [listing_page(("10001:甲 § 10002:乙", PAGE_X))])

    assert store.detail_link("10002") == DetailLink("10001", PAGE_X)
    assert RawStore(tmp_path, 2026).detail_link("10002") == store.detail_link("10002")


def test_only_the_code_seen_on_different_pages_is_a_conflict(tmp_path: Path) -> None:
    store = RawStore(tmp_path, 2026)
    store.save_listing("a", [listing_page(("10001:甲 § 10002:乙", PAGE_X))])
    store.save_listing("b", [listing_page(("10002:乙", PAGE_Y))])

    assert store.detail_link("10001") == DetailLink("10001", PAGE_X)
    with pytest.raises(ListingConflictError, match="10002 .*x/202610001 .*y/202610002"):
        store.detail_link("10002")


def test_conflict_is_also_detected_while_listings_are_being_saved(tmp_path: Path) -> None:
    store = RawStore(tmp_path, 2026)
    store.save_listing("a", [listing_page(("10001:甲 § 10002:乙", PAGE_X))])
    store.detail_link("10001")

    store.save_listing("b", [listing_page(("10002:乙", PAGE_Y))])

    assert store.has_listing("b")
    with pytest.raises(ListingConflictError, match="10002"):
        store.detail_link("10002")


def test_a_broken_listing_page_is_named_in_the_error(tmp_path: Path) -> None:
    store = RawStore(tmp_path, 2026)
    store.save_listing(
        "a",
        [
            "<table><tbody><tr><th>"
            "<a href='/r-syllabus/x/202610001'>10001:甲</a>"
            "</th></tr></tbody></table>"
        ],
    )

    with pytest.raises(ListingFormatError, match=r"a/1\.html: "):
        store.detail_link("10001")
