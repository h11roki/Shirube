import os
from pathlib import Path

from app.infrastructure.scrapers.ritsumeikan.listing import ListingRow, parse_listing

LISTING_DIR = "listings"
DETAIL_DIR = "details"
PAGE_SUFFIX = ".html"


class RawStore:
    def __init__(self, root: Path, year: int) -> None:
        self._listings = root / "ritsumeikan" / str(year) / LISTING_DIR
        self._details = root / "ritsumeikan" / str(year) / DETAIL_DIR
        self._rows: dict[str, ListingRow] | None = None

    def has_listing(self, key: str) -> bool:
        return (self._listings / key).is_dir()

    def save_listing(self, key: str, pages: list[str]) -> None:
        directory = self._listings / key
        for number, page in enumerate(pages, start=1):
            _write_atomically(directory / f"{number}{PAGE_SUFFIX}", page)
        directory.mkdir(parents=True, exist_ok=True)
        if self._rows is not None:
            self._rows.update(_rows_by_code(pages))

    def href_of(self, code: str) -> str | None:
        row = self._listed(code)
        return row.href if row else None

    def has_detail(self, code: str) -> bool:
        return self.detail_path(code).exists()

    def save_detail(self, code: str, page: str) -> None:
        _write_atomically(self.detail_path(code), page)

    def detail_path(self, code: str) -> Path:
        row = self._listed(code)
        return self._details / f"{row.code if row else code}{PAGE_SUFFIX}"

    def saved_detail_codes(self) -> list[str]:
        if not self._details.exists():
            return []
        return sorted(path.stem for path in self._details.glob(f"*{PAGE_SUFFIX}"))

    def _listed(self, code: str) -> ListingRow | None:
        if self._rows is None:
            self._rows = _rows_by_code(self._saved_listing_pages())
        return self._rows.get(code)

    def _saved_listing_pages(self) -> list[str]:
        if not self._listings.exists():
            return []
        paths = sorted(self._listings.glob(f"*/*{PAGE_SUFFIX}"))
        return [path.read_text(encoding="utf-8") for path in paths]


def _rows_by_code(pages: list[str]) -> dict[str, ListingRow]:
    rows: dict[str, ListingRow] = {}
    for page in pages:
        for row in parse_listing(page):
            for code in (row.code, *(alias.code for alias in row.aliases)):
                rows.setdefault(code, row)
    return rows


def _write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.part")
    partial.write_text(text, encoding="utf-8")
    os.replace(partial, path)
