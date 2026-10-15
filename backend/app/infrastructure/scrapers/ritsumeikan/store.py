import os
from pathlib import Path

from app.application.ports import DetailLink, ListingConflictError
from app.infrastructure.scrapers.ritsumeikan.listing import parse_listing

LISTING_DIR = "listings"
DETAIL_DIR = "details"
PAGE_SUFFIX = ".html"


class RawStore:
    def __init__(self, root: Path, year: int) -> None:
        self._listings = root / "ritsumeikan" / str(year) / LISTING_DIR
        self._details = root / "ritsumeikan" / str(year) / DETAIL_DIR
        self._links: dict[str, DetailLink] = {}
        self._conflicts: dict[str, DetailLink] = {}
        self._indexed = False

    def has_listing(self, key: str) -> bool:
        return (self._listings / key).is_dir()

    def save_listing(self, key: str, pages: list[str]) -> None:
        directory = self._listings / key
        for number, page in enumerate(pages, start=1):
            _write_atomically(directory / f"{number}{PAGE_SUFFIX}", page)
        directory.mkdir(parents=True, exist_ok=True)
        if self._indexed:
            self._index(pages)

    def detail_link(self, code: str) -> DetailLink | None:
        if not self._indexed:
            self._index(self._saved_listing_pages())
            self._indexed = True
        if code in self._conflicts:
            raise ListingConflictError(
                f"{code} が複数のページに現れます: "
                f"{self._links[code].href} {self._conflicts[code].href}"
            )
        return self._links.get(code)

    def has_detail(self, code: str) -> bool:
        return self.detail_path(code).exists()

    def save_detail(self, primary_code: str, page: str) -> None:
        _write_atomically(self.detail_path(primary_code), page)

    def detail_path(self, code: str) -> Path:
        return self._details / f"{code}{PAGE_SUFFIX}"

    def saved_detail_codes(self) -> list[str]:
        if not self._details.exists():
            return []
        return sorted(path.stem for path in self._details.glob(f"*{PAGE_SUFFIX}"))

    def _index(self, pages: list[str]) -> None:
        for page in pages:
            for row in parse_listing(page):
                link = DetailLink(row.code, row.href)
                for code in (row.code, *(alias.code for alias in row.aliases)):
                    if self._links.setdefault(code, link) != link:
                        self._conflicts[code] = link

    def _saved_listing_pages(self) -> list[str]:
        if not self._listings.exists():
            return []
        paths = sorted(self._listings.glob(f"*/*{PAGE_SUFFIX}"))
        return [path.read_text(encoding="utf-8") for path in paths]


def _write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.part")
    partial.write_text(text, encoding="utf-8")
    os.replace(partial, path)
