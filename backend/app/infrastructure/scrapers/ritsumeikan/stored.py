from app.domain.syllabus import Syllabus
from app.infrastructure.scrapers.ritsumeikan.detail import parse_detail
from app.infrastructure.scrapers.ritsumeikan.store import RawStore


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
        return parse_detail(self._store.detail_path(primary_code).read_text(encoding="utf-8"))
