from pathlib import Path

from app.application.fetch_syllabus import FetchSyllabus
from app.application.ports import ListingQuery
from app.infrastructure.scrapers.ritsumeikan.store import RawStore


def href_of(code: str) -> str:
    return f"/syllabus/s/r-syllabus/id{code}/2026{code}"


def listing_html(*titles: str) -> str:
    rows = "".join(
        f"<tr><th><a href='{href_of(title.partition(':')[0])}'>{title}</a></th>"
        "<td>理工学部</td><td>春セメスター</td><td>月1</td><td>BKC</td>"
        "<td>教員</td><td>日本語</td><td>2</td></tr>"
        for title in titles
    )
    return f"<table><tbody>{rows}</tbody></table>"


class FakeCatalog:
    def __init__(self, pages_by_key: dict[str, list[str]], lookups: dict[str, list[str]]) -> None:
        self.pages_by_key = pages_by_key
        self.lookups = lookups
        self.listing_calls: list[str] = []
        self.lookup_calls: list[str] = []
        self.detail_calls: list[str] = []

    def listing_queries(self) -> list[ListingQuery]:
        return [ListingQuery(key, "春学期", "月", 1) for key in self.pages_by_key]

    def listing_pages(self, query: ListingQuery) -> list[str]:
        self.listing_calls.append(query.key)
        return self.pages_by_key[query.key]

    def lookup_pages(self, code: str) -> list[str]:
        self.lookup_calls.append(code)
        return self.lookups.get(code, [listing_html()])

    def detail_page(self, href: str) -> str:
        self.detail_calls.append(href)
        return f"<html>{href}</html>"


def test_listings_are_saved_once_as_raw_pages(tmp_path: Path) -> None:
    catalog = FakeCatalog(
        {"a": [listing_html("10001:科目甲(A8)"), listing_html("10002:科目乙(A8)")], "b": []}, {}
    )
    store = RawStore(tmp_path, 2026)
    fetch = FetchSyllabus(catalog, store)

    fetch.listings()
    fetch.listings()

    assert catalog.listing_calls == ["a", "b"]
    assert (tmp_path / "ritsumeikan" / "2026" / "listings" / "a" / "2.html").read_text(
        encoding="utf-8"
    ) == listing_html("10002:科目乙(A8)")
    assert store.has_listing("b")
    assert RawStore(tmp_path, 2026).href_of("10002") == href_of("10002")


def test_details_come_from_the_index_then_from_a_code_lookup(tmp_path: Path) -> None:
    catalog = FakeCatalog(
        {"a": [listing_html("10001:科目甲(A8)")]},
        {"90002": [listing_html("1:科目丙(A8)", "90002:科目丁(A8)")]},
    )
    store = RawStore(tmp_path, 2026)
    fetch = FetchSyllabus(catalog, store)
    fetch.listings()

    missing = fetch.details(["10001", "90002", "30003"])

    assert catalog.lookup_calls == ["90002", "30003"]
    assert catalog.detail_calls == [href_of("10001"), href_of("90002")]
    assert (
        store.detail_path("10001").read_text(encoding="utf-8") == f"<html>{href_of('10001')}</html>"
    )
    assert missing == ["30003"]


def test_cross_listed_codes_share_the_page_of_the_primary_code(tmp_path: Path) -> None:
    catalog = FakeCatalog({"a": [listing_html("10001:科目甲(A8) § 10002:科目乙(A8)")]}, {})
    store = RawStore(tmp_path, 2026)
    fetch = FetchSyllabus(catalog, store)
    fetch.listings()

    missing = fetch.details(["10002", "10001"])

    assert missing == []
    assert catalog.lookup_calls == []
    assert catalog.detail_calls == [href_of("10001")]
    assert store.detail_path("10002") == store.detail_path("10001")
    assert store.detail_path("10001").name == "10001.html"
    assert RawStore(tmp_path, 2026).has_detail("10002")


def test_saved_details_and_lookups_are_not_fetched_again(tmp_path: Path) -> None:
    catalog = FakeCatalog({}, {})
    store = RawStore(tmp_path, 2026)
    store.save_detail("10001", "<html></html>")
    store.save_listing("code_30003", [listing_html()])

    missing = FetchSyllabus(catalog, store).details(["10001", "30003"])

    assert catalog.lookup_calls == []
    assert catalog.detail_calls == []
    assert missing == ["30003"]
