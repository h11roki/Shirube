import json
from dataclasses import asdict
from pathlib import Path

from app.infrastructure.scrapers.ritsumeikan.listing import ListingRow

LISTING_DIR = "listings"
DETAIL_DIR = "details"


class RawStore:
    def __init__(self, root: Path, year: int) -> None:
        self._listings = root / "ritsumeikan" / str(year) / LISTING_DIR
        self._details = root / "ritsumeikan" / str(year) / DETAIL_DIR

    def has_listing(self, key: str) -> bool:
        return self._listing_path(key).exists()

    def save_listing(self, key: str, rows: list[ListingRow]) -> None:
        self._listings.mkdir(parents=True, exist_ok=True)
        payload = [asdict(row) for row in rows]
        self._listing_path(key).write_text(json.dumps(payload, ensure_ascii=False, indent=1))

    def load_listings(self) -> dict[str, ListingRow]:
        index: dict[str, ListingRow] = {}
        for path in sorted(self._listings.glob("*.json")) if self._listings.exists() else []:
            for item in json.loads(path.read_text()):
                row = ListingRow(
                    **{
                        **item,
                        "faculties": tuple(item["faculties"]),
                        "instructors": tuple(item["instructors"]),
                    }
                )
                index.setdefault(row.code, row)
        return index

    def has_detail(self, code: str) -> bool:
        return self.detail_path(code).exists()

    def save_detail(self, code: str, html: str) -> None:
        self._details.mkdir(parents=True, exist_ok=True)
        self.detail_path(code).write_text(html, encoding="utf-8")

    def detail_path(self, code: str) -> Path:
        return self._details / f"{code}.html"

    def _listing_path(self, key: str) -> Path:
        return self._listings / f"{key}.json"
