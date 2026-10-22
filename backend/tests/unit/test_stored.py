from pathlib import Path

import pytest

from app.infrastructure.scrapers.ritsumeikan.detail import SyllabusFormatError
from app.infrastructure.scrapers.ritsumeikan.store import RawStore
from app.infrastructure.scrapers.ritsumeikan.stored import StoredSyllabi
from tests.unit.syllabus_pages import CIRCUITS_2, CROSS_LISTED, detail_page, listing_page

LISTING = listing_page(
    ("10004:架空平和研究 (GR) § 10005:架空交流演習(GR)", "/syllabus/s/r-syllabus/x/202610004")
)


def saved_store(tmp_path: Path, with_listing: bool) -> RawStore:
    store = RawStore(tmp_path, 2026)
    store.save_detail("10004", detail_page(CROSS_LISTED))
    if with_listing:
        store.save_listing("a", [LISTING])
    return store


def test_primary_code_is_read_without_listings(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=False)).syllabus("10004")

    assert syllabus is not None
    assert syllabus.title == "架空平和研究 (GR)"


def test_alias_code_resolves_to_the_primary_page_through_listings(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=True)).syllabus("10005")

    assert syllabus is not None
    assert syllabus.code == "10004"
    assert [alias.code for alias in syllabus.aliases] == ["10005"]


def test_unknown_or_unsaved_codes_are_none(tmp_path: Path) -> None:
    source = StoredSyllabi(saved_store(tmp_path, with_listing=False))

    assert source.syllabus("10005") is None
    assert source.syllabus("99999") is None


def test_every_saved_page_is_listed_once(tmp_path: Path) -> None:
    store = saved_store(tmp_path, with_listing=True)
    store.save_detail("10003", detail_page(CIRCUITS_2))

    assert [page.code for page in StoredSyllabi(store).syllabi()] == ["10003", "10004"]


def test_unreadable_page_is_named_in_the_error(tmp_path: Path) -> None:
    store = saved_store(tmp_path, with_listing=False)
    store.save_detail("10001", "<html><body></body></html>")

    with pytest.raises(SyllabusFormatError, match="^10001: 科目の見出し表"):
        StoredSyllabi(store).syllabi()


def test_the_page_url_comes_from_its_link_in_the_listings(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=True)).syllabus("10005")

    assert syllabus is not None
    assert syllabus.url == (
        "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/x/202610004?language=ja"
    )


def test_a_page_missing_from_the_listings_has_no_url(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=False)).syllabus("10004")

    assert syllabus is not None
    assert syllabus.url is None


def test_a_page_listed_with_two_links_has_no_url(tmp_path: Path) -> None:
    store = saved_store(tmp_path, with_listing=True)
    store.save_listing(
        "b", [listing_page(("10004:架空平和研究 (GR)", "/syllabus/s/r-syllabus/y/202610004"))]
    )

    assert [page.url for page in StoredSyllabi(store).syllabi()] == [None]


def test_a_page_listed_only_as_an_alias_of_another_has_no_url(tmp_path: Path) -> None:
    store = RawStore(tmp_path, 2026)
    store.save_detail("10005", detail_page(CROSS_LISTED))
    store.save_listing("a", [LISTING])

    assert [page.url for page in StoredSyllabi(store).syllabi()] == [None]
