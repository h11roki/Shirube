import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

DETAIL_LINK = "a[href*='r-syllabus']"
CELL_COUNT = 7
FACULTY_SEPARATOR = ","
NAME_SEPARATOR = "、"
PAGE_COUNT = re.compile(r"全\s*(\d+)\s*件（\s*(\d+)\s*/\s*(\d+)\s*ページ）")


class ListingFormatError(ValueError):
    pass


@dataclass(frozen=True)
class ListingRow:
    code: str
    title: str
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
        if not isinstance(href, str) or len(cells) < CELL_COUNT:
            raise ListingFormatError(f"一覧の行を読めません: {tr.get_text(' ', strip=True)[:80]!r}")
        code, _, title = link.get_text(strip=True).partition(":")
        faculties, term_label, slot_label, campus, instructors, language, credits = cells[
            :CELL_COUNT
        ]
        rows.append(
            ListingRow(
                code=code,
                title=title,
                faculties=tuple(name.strip() for name in faculties.split(FACULTY_SEPARATOR)),
                term_label=term_label,
                slot_label=slot_label,
                campus=campus,
                instructors=tuple(
                    n.strip() for n in instructors.split(NAME_SEPARATOR) if n.strip()
                ),
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
