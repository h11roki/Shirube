from pathlib import Path

from app.infrastructure.scrapers.ritsumeikan.crawler import crawl_details, crawl_listings
from app.infrastructure.scrapers.ritsumeikan.listing import ListingRow
from app.infrastructure.scrapers.ritsumeikan.store import RawStore


def listing(code: str) -> ListingRow:
    return ListingRow(
        code=code,
        title=f"科目{code}(A8)",
        faculties=("理工学部",),
        term_label="春セメスター",
        slot_label="月1",
        campus="BKC",
        instructors=("教員",),
        language="日本語",
        credits="2",
        href=f"/syllabus/s/r-syllabus/id{code}/2026{code}",
    )


class FakePortal:
    def __init__(self, rows_by_search: dict[str, list[ListingRow]] | None = None) -> None:
        self.rows_by_search = rows_by_search or {}
        self.searches: list[tuple[str, str | None, int | None]] = []
        self.code_searches: list[str] = []
        self.detail_hrefs: list[str] = []

    def search(self, term: str, weekday: str | None, period: int | None) -> list[ListingRow]:
        self.searches.append((term, weekday, period))
        return self.rows_by_search.get(f"{term}_{weekday}_{period}", [])

    def search_code(self, code: str) -> list[ListingRow]:
        self.code_searches.append(code)
        return [listing(code)] if code.startswith("9") else []

    def detail_html(self, href: str) -> str:
        self.detail_hrefs.append(href)
        return f"<html>{href}</html>"


def test_listings_cover_every_term_weekday_and_period_once(tmp_path: Path) -> None:
    portal = FakePortal({"春学期_月_1": [listing("10001")]})
    store = RawStore(tmp_path, 2026)

    crawl_listings(portal, store)
    crawl_listings(portal, store)

    assert len(portal.searches) == 3 * 7 * 7 + 2
    assert ("夏期集中", None, None) in portal.searches
    assert store.load_listings() == {"10001": listing("10001")}


def test_details_use_the_listing_index_then_fall_back_to_a_code_search(tmp_path: Path) -> None:
    portal = FakePortal({"春学期_月_1": [listing("10001")]})
    store = RawStore(tmp_path, 2026)
    crawl_listings(portal, store)

    missing = crawl_details(portal, store, ["10001", "90002", "30003"])

    assert portal.code_searches == ["90002", "30003"]
    assert portal.detail_hrefs == [listing("10001").href, listing("90002").href]
    assert (
        store.detail_path("10001").read_text(encoding="utf-8")
        == f"<html>{listing('10001').href}</html>"
    )
    assert missing == ["30003"]


def test_details_already_saved_are_not_fetched_again(tmp_path: Path) -> None:
    portal = FakePortal()
    store = RawStore(tmp_path, 2026)
    store.save_detail("10001", "<html></html>")

    crawl_details(portal, store, ["10001"])

    assert portal.detail_hrefs == []
    assert portal.code_searches == []
