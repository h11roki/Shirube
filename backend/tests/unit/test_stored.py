from pathlib import Path

import pytest

from app.infrastructure.scrapers.ritsumeikan.detail import SyllabusFormatError
from app.infrastructure.scrapers.ritsumeikan.store import RawStore
from app.infrastructure.scrapers.ritsumeikan.stored import StoredSyllabi
from tests.unit.listing_page import listing_page

FIXTURES = Path(__file__).parents[1] / "fixtures" / "html" / "ritsumeikan"
LISTING = listing_page(
    (
        "16806:平和人権フィールドスタディ (GR) § 16807:国際平和交流セミナー(GR)",
        "/syllabus/s/r-syllabus/x/202616806",
    )
)


def saved_store(tmp_path: Path, with_listing: bool) -> RawStore:
    store = RawStore(tmp_path, 2026)
    store.save_detail("16806", (FIXTURES / "detail_16806.html").read_text(encoding="utf-8"))
    if with_listing:
        store.save_listing("a", [LISTING])
    return store


def test_primary_code_is_read_without_listings(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=False)).syllabus("16806")

    assert syllabus is not None
    assert syllabus.title == "平和人権フィールドスタディ (GR)"


def test_alias_code_resolves_to_the_primary_page_through_listings(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=True)).syllabus("16807")

    assert syllabus is not None
    assert syllabus.code == "16806"
    assert [alias.code for alias in syllabus.aliases] == ["16807"]


def test_unknown_or_unsaved_codes_are_none(tmp_path: Path) -> None:
    source = StoredSyllabi(saved_store(tmp_path, with_listing=False))

    assert source.syllabus("16807") is None
    assert source.syllabus("99999") is None


def test_every_saved_page_is_listed_once(tmp_path: Path) -> None:
    store = saved_store(tmp_path, with_listing=True)
    store.save_detail("32494", (FIXTURES / "detail_32494.html").read_text(encoding="utf-8"))

    assert [page.code for page in StoredSyllabi(store).syllabi()] == ["16806", "32494"]


def test_unreadable_page_is_named_in_the_error(tmp_path: Path) -> None:
    store = saved_store(tmp_path, with_listing=False)
    store.save_detail("10001", "<html><body></body></html>")

    with pytest.raises(SyllabusFormatError, match="^10001: 科目の見出し表"):
        StoredSyllabi(store).syllabi()


def test_the_page_url_comes_from_its_link_in_the_listings(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=True)).syllabus("16807")

    assert syllabus is not None
    assert syllabus.url == (
        "https://syllabus.ritsumei.ac.jp/syllabus/s/r-syllabus/x/202616806?language=ja"
    )


def test_a_page_missing_from_the_listings_has_no_url(tmp_path: Path) -> None:
    syllabus = StoredSyllabi(saved_store(tmp_path, with_listing=False)).syllabus("16806")

    assert syllabus is not None
    assert syllabus.url is None


def test_a_page_listed_with_two_links_has_no_url(tmp_path: Path) -> None:
    store = saved_store(tmp_path, with_listing=True)
    store.save_listing(
        "b",
        [
            listing_page(
                ("16806:平和人権フィールドスタディ (GR)", "/syllabus/s/r-syllabus/y/202616806")
            )
        ],
    )

    assert [page.url for page in StoredSyllabi(store).syllabi()] == [None]
