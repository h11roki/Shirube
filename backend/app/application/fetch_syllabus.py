import logging
from collections.abc import Iterable

from app.application.ports import DetailLink, ListingConflictError, RawPages, SyllabusCatalog

LOOKUP_KEY_PREFIX = "code_"

logger = logging.getLogger(__name__)


class FetchSyllabus:
    def __init__(self, catalog: SyllabusCatalog, pages: RawPages) -> None:
        self._catalog = catalog
        self._pages = pages

    def listings(self) -> None:
        for query in self._catalog.listing_queries():
            if self._pages.has_listing(query.key):
                continue
            pages = self._catalog.listing_pages(query)
            self._pages.save_listing(query.key, pages)
            logger.info("%s: %d ページ", query.key, len(pages))

    def details(self, codes: Iterable[str]) -> list[str]:
        missing: list[str] = []
        for code in codes:
            if self._pages.has_detail(code):
                continue
            try:
                link = self._pages.detail_link(code) or self._looked_up_link(code)
            except ListingConflictError as error:
                missing.append(code)
                logger.warning("%s", error)
                continue
            if link is None:
                missing.append(code)
                logger.warning("%s: 見つからない", code)
                continue
            if self._pages.has_detail(link.primary_code):
                continue
            self._pages.save_detail(link.primary_code, self._catalog.detail_page(link.href))
            logger.info("%s: 保存 (%s)", code, link.primary_code)
        return missing

    def _looked_up_link(self, code: str) -> DetailLink | None:
        key = f"{LOOKUP_KEY_PREFIX}{code}"
        if not self._pages.has_listing(key):
            self._pages.save_listing(key, self._catalog.lookup_pages(code))
        return self._pages.detail_link(code)
