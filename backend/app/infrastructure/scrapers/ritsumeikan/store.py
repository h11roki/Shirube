import os
from pathlib import Path

from app.application.ports import DetailLink
from app.infrastructure.scrapers.ritsumeikan.listing import parse_listing

LISTING_DIR = "listings"
DETAIL_DIR = "details"
PAGE_SUFFIX = ".html"


class ListingConflictError(ValueError):
    pass


class RawStore:
    def __init__(self, root: Path, year: int) -> None:
        self._listings = root / "ritsumeikan" / str(year) / LISTING_DIR
        self._details = root / "ritsumeikan" / str(year) / DETAIL_DIR
        self._links: dict[str, DetailLink] | None = None
        self._conflicts: dict[str, DetailLink] = {}

    def has_listing(self, key: str) -> bool:
        return (self._listings / key).is_dir()

    def save_listing(self, key: str, pages: list[str]) -> None:
        directory = self._listings / key
        for number, page in enumerate(pages, start=1):
            _write_atomically(directory / f"{number}{PAGE_SUFFIX}", page)
        directory.mkdir(parents=True, exist_ok=True)
        if self._links is not None:
            _index(self._links, self._conflicts, pages)

    def detail_link(self, code: str) -> DetailLink | None:
        if self._links is None:
            links: dict[str, DetailLink] = {}
            _index(links, self._conflicts, self._saved_listing_pages())
            self._links = links
        if code in self._conflicts:
            raise ListingConflictError(
                f"{code} が複数のページに現れます: "
                f"{self._links[code].href} {self._conflicts[code].href}"
            )
        return self._links.get(code)

    def has_detail(self, primary_code: str) -> bool:
        return self.detail_path(primary_code).exists()

    def save_detail(self, primary_code: str, page: str) -> None:
        _write_atomically(self.detail_path(primary_code), page)

    def detail_path(self, primary_code: str) -> Path:
        return self._details / f"{primary_code}{PAGE_SUFFIX}"

    def saved_detail_codes(self) -> list[str]:
        if not self._details.exists():
            return []
        return sorted(path.stem for path in self._details.glob(f"*{PAGE_SUFFIX}"))

    def _saved_listing_pages(self) -> list[str]:
        if not self._listings.exists():
            return []
        paths = sorted(self._listings.glob(f"*/*{PAGE_SUFFIX}"))
        return [path.read_text(encoding="utf-8") for path in paths]


def _index(
    links: dict[str, DetailLink], conflicts: dict[str, DetailLink], pages: list[str]
) -> None:
    for page in pages:
        for row in parse_listing(page):
            link = DetailLink(row.code, row.href)
            for code in (row.code, *(alias.code for alias in row.aliases)):
                if links.setdefault(code, link) != link:
                    conflicts[code] = link


def _write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.part")
    partial.write_text(text, encoding="utf-8")
    os.replace(partial, path)
