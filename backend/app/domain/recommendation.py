from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

from app.domain.occupation import OccupationProfile
from app.domain.ranking import CourseMatch
from app.domain.syllabus import Syllabus


class Relevance(Enum):
    CORE = "core"
    FOUNDATION = "foundation"


class RecommendationError(ValueError):
    pass


def _require_candidates(names: Iterable[str], candidates: Iterable[str]) -> None:
    unknown = sorted(set(names) - set(candidates))
    if unknown:
        raise RecommendationError(f"候補に無い科目が選ばれています: {'、'.join(unknown)}")


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
    candidates: tuple[str, ...]

    def __post_init__(self) -> None:
        counts = Counter(course.name for course in self.courses)
        repeated = sorted(name for name, count in counts.items() if count > 1)
        if repeated:
            raise RecommendationError(f"同じ科目が 2 回選ばれています: {'、'.join(repeated)}")
        _require_candidates(counts, self.candidates)


def arrange(
    profile: OccupationProfile, matches: Sequence[CourseMatch], choices: Sequence[CourseChoice]
) -> Recommendation:
    ranked = {match.name: (rank, match) for rank, match in enumerate(matches)}
    _require_candidates((choice.name for choice in choices), ranked)
    group = {relevance: index for index, relevance in enumerate(Relevance)}
    kept: dict[str, CourseChoice] = {}
    for choice in choices:
        earlier = kept.get(choice.name)
        if earlier is None or group[choice.relevance] < group[earlier.relevance]:
            kept[choice.name] = choice
    ordered = sorted(
        kept.values(), key=lambda choice: (group[choice.relevance], ranked[choice.name][0])
    )
    courses = tuple(
        RecommendedCourse(
            choice.name, ranked[choice.name][1].syllabus_code, choice.relevance, choice.reason
        )
        for choice in ordered
    )
    return Recommendation(profile, courses, tuple(match.name for match in matches))
