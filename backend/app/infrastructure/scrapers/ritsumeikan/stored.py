import logging
from dataclasses import replace

from app.application.ports import ListingConflictError
from app.domain.syllabus import Syllabus
from app.infrastructure.scrapers.ritsumeikan.detail import SyllabusFormatError, parse_detail
from app.infrastructure.scrapers.ritsumeikan.listing import detail_url
from app.infrastructure.scrapers.ritsumeikan.store import RawStore

logger = logging.getLogger(__name__)


class StoredSyllabi:
    def __init__(self, store: RawStore) -> None:
        self._store = store

    def syllabus(self, code: str) -> Syllabus | None:
        primary = code
        if not self._store.has_detail(primary):
            link = self._store.detail_link(code)
            if link is None or not self._store.has_detail(link.primary_code):
                return None
            primary = link.primary_code
        return self._parsed(primary)

    def syllabi(self) -> list[Syllabus]:
        return [self._parsed(code) for code in self._store.saved_detail_codes()]

    def _parsed(self, primary_code: str) -> Syllabus:
        try:
            page = parse_detail(self._store.detail_path(primary_code).read_text(encoding="utf-8"))
        except SyllabusFormatError as error:
            raise SyllabusFormatError(f"{primary_code}: {error}") from error
        return replace(page, url=self._url(primary_code))

    def _url(self, primary_code: str) -> str | None:
        try:
            link = self._store.detail_link(primary_code)
        except ListingConflictError as error:
            logger.warning("原ページの URL を決められません: %s", error)
            return None
        return None if link is None else detail_url(link.href)
