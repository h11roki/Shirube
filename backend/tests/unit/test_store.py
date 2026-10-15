from pathlib import Path

import pytest

from app.application.ports import DetailLink
from app.infrastructure.scrapers.ritsumeikan.store import ListingConflictError, RawStore


def listing_html(title: str, href: str) -> str:
    return (
        f"<table><tbody><tr><th><a href='{href}'>{title}</a></th>"
        "<td>理工学部</td><td>春セメスター</td><td>月1</td><td>BKC</td>"
        "<td>甲</td><td>日本語</td><td>2</td></tr></tbody></table>"
    )


def test_same_code_on_the_same_page_in_two_listings_is_one_link(tmp_path: Path) -> None:
    store = RawStore(tmp_path, 2026)
    store.save_listing("a", [listing_html("10001:甲 § 10002:乙", "/r-syllabus/x/202610001")])
    store.save_listing("b", [listing_html("10001:甲 § 10002:乙", "/r-syllabus/x/202610001")])

    assert store.detail_link("10002") == DetailLink("10001", "/r-syllabus/x/202610001")
    assert RawStore(tmp_path, 2026).detail_link("10002") == store.detail_link("10002")


def test_same_code_on_different_pages_is_a_conflict(tmp_path: Path) -> None:
    store = RawStore(tmp_path, 2026)
    store.save_listing("a", [listing_html("10001:甲 § 10002:乙", "/r-syllabus/x/202610001")])
    store.save_listing("b", [listing_html("10002:乙", "/r-syllabus/y/202610002")])

    with pytest.raises(ListingConflictError, match="10002"):
        store.detail_link("10002")


def test_conflict_is_also_detected_while_listings_are_being_saved(tmp_path: Path) -> None:
    store = RawStore(tmp_path, 2026)
    store.save_listing("a", [listing_html("10001:甲 § 10002:乙", "/r-syllabus/x/202610001")])
    store.detail_link("10001")

    with pytest.raises(ListingConflictError, match="10002"):
        store.save_listing("b", [listing_html("10002:乙", "/r-syllabus/y/202610002")])
