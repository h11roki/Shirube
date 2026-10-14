from dataclasses import dataclass
from typing import Protocol

from app.domain.course import CourseSection


class TimetableSource(Protocol):
    def sections(self) -> list[CourseSection]: ...


@dataclass(frozen=True)
class ListingQuery:
    key: str
    term: str
    weekday: str | None
    period: int | None


class SyllabusCatalog(Protocol):
    def listing_queries(self) -> list[ListingQuery]: ...

    def listing_pages(self, query: ListingQuery) -> list[str]: ...

    def lookup_pages(self, code: str) -> list[str]: ...

    def detail_page(self, href: str) -> str: ...


class RawPages(Protocol):
    def has_listing(self, key: str) -> bool: ...

    def save_listing(self, key: str, pages: list[str]) -> None: ...

    def href_of(self, code: str) -> str | None: ...

    def has_detail(self, code: str) -> bool: ...

    def save_detail(self, code: str, page: str) -> None: ...
