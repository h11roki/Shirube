from app.domain.syllabus import Syllabus
from app.infrastructure.scrapers.ritsumeikan.detail import parse_detail
from app.infrastructure.scrapers.ritsumeikan.store import RawStore


class StoredSyllabi:
    def __init__(self, store: RawStore) -> None:
        self._store = store

    def syllabus(self, code: str) -> Syllabus | None:
        path = self._store.detail_path(code)
        if not path.exists():
            return None
        return parse_detail(path.read_text(encoding="utf-8"))
