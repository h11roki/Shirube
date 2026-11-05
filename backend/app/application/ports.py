from collections.abc import Callable, Iterable, Mapping, Sequence, Set
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol
from uuid import UUID

from app.application.fingerprint import fingerprint_of
from app.application.reason_judging import ReasonCase, ReasonVote
from app.domain.chunk import SyllabusChunk
from app.domain.course import CourseSection
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan, PlanListing, PlanResult, PlanStage
from app.domain.quota import PlanCounts
from app.domain.ranking import ChunkHit
from app.domain.recommendation import CandidateCourse, CourseChoice, Recommendation
from app.domain.roadmap import Semester
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

    def syllabus_urls(self, year: int, primary_codes: Set[str]) -> dict[str, str]: ...


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


class ReasonJudgeError(ValueError):
    pass


class ReasonJudgeUnavailableError(ValueError):
    pass


class ReasonJudge(Protocol):
    def judge(self, case: ReasonCase) -> ReasonVote: ...


class ClassificationError(ValueError):
    def __init__(self, message: str, input_tokens: int = 0) -> None:
        super().__init__(message)
        self.input_tokens = input_tokens


@dataclass(frozen=True)
class CourseOdds:
    name: str
    core: float
    foundation: float
    unrelated: float


@dataclass(frozen=True)
class Classification:
    odds: tuple[CourseOdds, ...]
    input_tokens: int


class CourseClassifier(Protocol):
    def classify(
        self, profile: OccupationProfile, candidates: Sequence[CandidateCourse]
    ) -> Classification: ...


@dataclass(frozen=True)
class TokenUsage:
    input: int
    cached: int
    output: int

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            self.input + other.input, self.cached + other.cached, self.output + other.output
        )


def total_usage(usages: Iterable[Mapping[str, TokenUsage]]) -> dict[str, TokenUsage]:
    total: dict[str, TokenUsage] = {}
    for usage in usages:
        for model, tokens in usage.items():
            total[model] = total[model] + tokens if model in total else tokens
    return dict(sorted(total.items()))


class UsageMeter(Protocol):
    def meter(self) -> AbstractContextManager[Callable[[], dict[str, TokenUsage]]]: ...


class InvalidTokenError(ValueError):
    pass


class TokenVerifier(Protocol):
    def subject_of(self, token: str) -> str: ...


class Deletion(Enum):
    DELETED = "deleted"
    MISSING = "missing"
    RUNNING = "running"


class PlanRunningError(ValueError):
    pass


class UserRepository(Protocol):
    def id_of(self, subject: str) -> UUID: ...

    def taken(self, user_id: UUID) -> frozenset[str]: ...

    def add_taken(self, user_id: UUID, name: str) -> None: ...

    def remove_taken(self, user_id: UUID, name: str) -> None: ...

    def delete(self, user_id: UUID, since: datetime) -> Deletion: ...


class PlanFormatError(ValueError):
    pass


class PlanRepository(Protocol):
    def add(self, plan: Plan, since: datetime, admit: Callable[[PlanCounts], None]) -> None: ...

    def claim_next(self) -> Plan | None: ...

    def claim(self, plan_id: UUID) -> Plan | None: ...

    def enter_stage(self, plan_id: UUID, stage: PlanStage) -> None: ...

    def finish(self, plan: Plan) -> bool: ...

    def replace_result(self, plan: Plan, previous: PlanResult) -> bool: ...

    def fail_stalled(self, after: timedelta, failure: str) -> list[UUID]: ...

    def delete_owned_by(self, plan_id: UUID, owner_id: UUID, since: datetime) -> Deletion: ...

    def purge_deleted(self, before: datetime) -> int: ...

    def get(self, plan_id: UUID) -> Plan | None: ...

    def get_owned_by(self, plan_id: UUID, owner_id: UUID) -> Plan | None: ...

    def list_owned_by(self, owner_id: UUID, limit: int) -> PlanListing: ...


@dataclass(frozen=True)
class RecommendationKey:
    occupation: str
    department: str
    year: int
    semesters: tuple[Semester, ...]
    left_out: tuple[str, ...]
    fingerprint: str

    @property
    def digest(self) -> str:
        parts = (
            self.occupation,
            self.department,
            str(self.year),
            ",".join(f"{semester.grade}-{semester.term.value}" for semester in self.semesters),
            "\n".join(self.left_out),
            self.fingerprint,
        )
        return fingerprint_of(parts)


class RecommendationStore(Protocol):
    def recall(self, key: RecommendationKey, now: datetime) -> Recommendation | None: ...

    def remember(
        self, key: RecommendationKey, recommendation: Recommendation, until: datetime
    ) -> None: ...

    def forget_expired(self, now: datetime) -> int: ...

    def forget_all(self) -> int: ...


class BuildOutcome(Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DISCARDED = "discarded"
    STALLED = "stalled"


@dataclass(frozen=True)
class FailureCause:
    types: tuple[str, ...]
    code: str | None = None


@dataclass(frozen=True)
class PlanBuild:
    outcome: BuildOutcome
    cause: FailureCause | None = None
    seconds: Mapping[PlanStage, float] = field(default_factory=dict)
    usage: Mapping[str, TokenUsage] = field(default_factory=dict)


@dataclass(frozen=True)
class RecordedBuild:
    finished_at: datetime
    queued_seconds: float | None
    build: PlanBuild


class PlanBuildLog(Protocol):
    def record(self, plan_id: UUID, build: PlanBuild) -> None: ...

    def since(self, start: datetime) -> list[RecordedBuild]: ...


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
