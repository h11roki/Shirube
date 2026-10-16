from collections import Counter
from dataclasses import dataclass
from enum import Enum

from app.domain.occupation import OccupationProfile
from app.domain.syllabus import Syllabus


class Relevance(Enum):
    CORE = "core"
    FOUNDATION = "foundation"


RELEVANCE_ORDER = (Relevance.CORE, Relevance.FOUNDATION)


class RecommendationError(ValueError):
    pass


@dataclass(frozen=True)
class CandidateCourse:
    name: str
    syllabus: Syllabus


@dataclass(frozen=True)
class CourseChoice:
    name: str
    relevance: Relevance
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise RecommendationError(f"{self.name}: 理由が空です")


@dataclass(frozen=True)
class RecommendedCourse:
    name: str
    syllabus_code: str
    relevance: Relevance
    reason: str


@dataclass(frozen=True)
class Recommendation:
    profile: OccupationProfile
    courses: tuple[RecommendedCourse, ...]
    considered: int

    def __post_init__(self) -> None:
        counts = Counter(course.name for course in self.courses)
        repeated = sorted(name for name, count in counts.items() if count > 1)
        if repeated:
            raise RecommendationError(f"同じ科目が 2 回選ばれています: {'、'.join(repeated)}")
