from collections.abc import Set
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol
from uuid import UUID

from app.domain.chunk import SyllabusChunk
from app.domain.course import CourseSection
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan, PlanResult, PlanStage, PlanSummary
from app.domain.ranking import ChunkHit
from app.domain.recommendation import CandidateCourse, CourseChoice
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

    def syllabi(self, year: int) -> list[Syllabus]: ...

    def syllabi_of(self, year: int, primary_codes: Set[str]) -> dict[str, Syllabus]: ...

    def syllabus_codes(self, year: int) -> dict[str, str]: ...


class Embedder(Protocol):
    @property
    def model(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class EmbeddingError(ValueError):
    pass


class OccupationAnalysisError(ValueError):
    pass


class OccupationAnalyzer(Protocol):
    def analyze(self, occupation: str) -> OccupationProfile: ...


class CourseSelectionError(ValueError):
    pass


class CourseSelector(Protocol):
    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]: ...


class InvalidTokenError(ValueError):
    pass


class TokenVerifier(Protocol):
    def subject_of(self, token: str) -> str: ...


class UserRepository(Protocol):
    def id_of(self, subject: str) -> UUID: ...

    def add_taken(self, user_id: UUID, name: str) -> None: ...

    def remove_taken(self, user_id: UUID, name: str) -> None: ...


class PlanFormatError(ValueError):
    pass


class PlanRepository(Protocol):
    def add(self, plan: Plan) -> None: ...

    def claim_next(self) -> Plan | None: ...

    def claim(self, plan_id: UUID) -> Plan | None: ...

    def enter_stage(self, plan_id: UUID, stage: PlanStage) -> None: ...

    def finish(self, plan: Plan) -> bool: ...

    def replace_result(self, plan: Plan, previous: PlanResult) -> bool: ...

    def fail_stalled(self, after: timedelta, failure: str) -> list[UUID]: ...

    def get(self, plan_id: UUID) -> Plan | None: ...

    def get_owned_by(self, plan_id: UUID, owner_id: UUID) -> Plan | None: ...

    def list_owned_by(self, owner_id: UUID, limit: int) -> list[PlanSummary]: ...


class ChunkRepository(Protocol):
    def embedded_hashes(self, model: str, hashes: set[str]) -> set[str]: ...

    def save_embeddings(self, model: str, vectors: dict[str, list[float]]) -> None: ...

    def replace_chunks(self, year: int, chunks: list[SyllabusChunk]) -> None: ...

    def years_not_embedded(self, model: str) -> list[int]: ...

    def prune_embeddings(self, model: str) -> int: ...


class ChunkSearch(Protocol):
    def is_embedded(self, year: int, model: str) -> bool: ...

    def best_chunks(
        self, year: int, model: str, vector: list[float], syllabus_codes: set[str]
    ) -> list[ChunkHit]: ...


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
