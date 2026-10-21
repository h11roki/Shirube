import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from app.domain.syllabus import CourseName
from app.infrastructure.scrapers.ritsumeikan.text import (
    FACULTY_SEPARATOR,
    NAME_SEPARATOR,
    split_list,
    split_titles,
)

DETAIL_LINK = "a[href*='r-syllabus']"
CELL_COUNT = 7
PAGE_COUNT = re.compile(r"全\s*(\d+)\s*件（\s*(\d+)\s*/\s*(\d+)\s*ページ）")


class ListingFormatError(ValueError):
    pass


@dataclass(frozen=True)
class ListingRow:
    code: str
    title: str
    aliases: tuple[CourseName, ...]
    faculties: tuple[str, ...]
    term_label: str
    slot_label: str
    campus: str
    instructors: tuple[str, ...]
    language: str
    credits: str
    href: str


@dataclass(frozen=True)
class PageCount:
    total_rows: int
    current: int
    last: int


def parse_listing(html: str) -> list[ListingRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[ListingRow] = []
    for tr in soup.select("table tbody tr"):
        link = tr.select_one(DETAIL_LINK)
        if link is None:
            continue
        href = link.get("href")
        cells = [cell.get_text(" ", strip=True) for cell in _cells_after_link(tr)]
        if not isinstance(href, str) or not href.startswith("/") or len(cells) < CELL_COUNT:
            raise ListingFormatError(f"一覧の行を読めません: {tr.get_text(' ', strip=True)[:80]!r}")
        try:
            primary, *aliases = split_titles(link.get_text(strip=True))
        except ValueError as error:
            raise ListingFormatError(str(error)) from error
        faculties, term_label, slot_label, campus, instructors, language, credits = cells[
            :CELL_COUNT
        ]
        rows.append(
            ListingRow(
                code=primary.code,
                title=primary.title,
                aliases=tuple(aliases),
                faculties=split_list(faculties, FACULTY_SEPARATOR),
                term_label=term_label,
                slot_label=slot_label,
                campus=campus,
                instructors=split_list(instructors, NAME_SEPARATOR),
                language=language,
                credits=credits,
                href=href,
            )
        )
    return rows


def _cells_after_link(tr: Tag) -> list[Tag]:
    cells = tr.find_all(["th", "td"])
    after_link = [i for i, cell in enumerate(cells) if cell.select_one(DETAIL_LINK) is not None]
    return cells[after_link[0] + 1 :] if after_link else []


def parse_page_count(text: str) -> PageCount | None:
    matched = PAGE_COUNT.search(text)
    if matched is None:
        return None
    total_rows, current, last = (int(group) for group in matched.groups())
    return PageCount(total_rows=total_rows, current=current, last=last)
