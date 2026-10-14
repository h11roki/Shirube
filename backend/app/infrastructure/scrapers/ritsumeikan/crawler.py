import logging
from collections.abc import Iterable
from typing import Protocol

from app.infrastructure.scrapers.ritsumeikan.listing import ListingRow
from app.infrastructure.scrapers.ritsumeikan.store import RawStore

TERMS_WITH_SLOTS = ("春学期", "秋学期", "通年")
TERMS_WITHOUT_SLOTS = ("夏期集中", "冬期集中")
WEEKDAYS = ("月", "火", "水", "木", "金", "土", "日")
PERIODS = range(1, 8)

logger = logging.getLogger(__name__)


class Portal(Protocol):
    def search(self, term: str, weekday: str | None, period: int | None) -> list[ListingRow]: ...

    def search_code(self, code: str) -> list[ListingRow]: ...

    def detail_html(self, href: str) -> str: ...


def crawl_listings(portal: Portal, store: RawStore) -> None:
    searches: list[tuple[str, str, str | None, int | None]] = [
        (f"{term}_{weekday}_{period}", term, weekday, period)
        for term in TERMS_WITH_SLOTS
        for weekday in WEEKDAYS
        for period in PERIODS
    ]
    searches += [(term, term, None, None) for term in TERMS_WITHOUT_SLOTS]
    for key, term, weekday, period in searches:
        if store.has_listing(key):
            continue
        rows = portal.search(term, weekday, period)
        store.save_listing(key, rows)
        logger.info("%s: %d 件", key, len(rows))


def crawl_details(portal: Portal, store: RawStore, codes: Iterable[str]) -> list[str]:
    index = store.load_listings()
    missing: list[str] = []
    for code in codes:
        if store.has_detail(code):
            continue
        row = index.get(code) or next(iter(portal.search_code(code)), None)
        if row is None or row.code != code:
            missing.append(code)
            logger.warning("%s: 一覧に見つからない", code)
            continue
        store.save_detail(code, portal.detail_html(row.href))
        logger.info("%s: 保存", code)
    return missing
