from dataclasses import dataclass
from typing import Protocol

from app.domain.course import CourseSection
from app.domain.syllabus import Syllabus


class TimetableSource(Protocol):
    def sections(self) -> list[CourseSection]: ...


class SyllabusSource(Protocol):
    def syllabus(self, code: str) -> Syllabus | None: ...

    def syllabi(self) -> list[Syllabus]: ...


class CourseRepository(Protocol):
    def replace_sections(self, year: int, sections: list[CourseSection]) -> None: ...

    def replace_syllabi(self, year: int, syllabi: list[Syllabus]) -> None: ...

    def sections(self, year: int) -> list[CourseSection]: ...

    def syllabus(self, year: int, code: str) -> Syllabus | None: ...


@dataclass(frozen=True)
class ListingQuery:
    key: str
    term: str
    weekday: str | None
    period: int | None


@dataclass(frozen=True)
class DetailLink:
    primary_code: str
    href: str


class ListingConflictError(ValueError):
    pass


class SyllabusCatalog(Protocol):
    def listing_queries(self) -> list[ListingQuery]: ...

    def listing_pages(self, query: ListingQuery) -> list[str]: ...

    def lookup_pages(self, code: str) -> list[str]: ...

    def detail_page(self, href: str) -> str: ...


class RawPages(Protocol):
    def has_listing(self, key: str) -> bool: ...

    def save_listing(self, key: str, pages: list[str]) -> None: ...

    def detail_link(self, code: str) -> DetailLink | None: ...

    def has_detail(self, code: str) -> bool: ...

    def save_detail(self, primary_code: str, page: str) -> None: ...
