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


def _require_link(name: str, relevance: Relevance, prerequisite_for: str | None) -> None:
    if relevance is Relevance.CORE and prerequisite_for is not None:
        raise RecommendationError(f"{name}: 中心の科目が前提にする科目を指しています")
    if relevance is Relevance.FOUNDATION and prerequisite_for is None:
        raise RecommendationError(f"{name}: 土台の科目が前提にする中心の科目を指していません")


@dataclass(frozen=True)
class CourseChoice:
    name: str
    relevance: Relevance
    reason: str
    prerequisite_for: str | None = None

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise RecommendationError(f"{self.name}: 理由が空です")
        _require_link(self.name, self.relevance, self.prerequisite_for)


@dataclass(frozen=True)
class RecommendedCourse:
    name: str
    syllabus_code: str
    relevance: Relevance
    reason: str
    prerequisite_for: str | None = None

    def __post_init__(self) -> None:
        _require_link(self.name, self.relevance, self.prerequisite_for)


@dataclass(frozen=True)
class Recommendation:
    profile: OccupationProfile
    courses: tuple[RecommendedCourse, ...]
    candidates: tuple[str, ...]
    unlinked: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        counts = Counter(course.name for course in self.courses)
        repeated = sorted(name for name, count in counts.items() if count > 1)
        if repeated:
            raise RecommendationError(f"同じ科目が 2 回選ばれています: {'、'.join(repeated)}")
        _require_candidates([*counts, *self.unlinked], self.candidates)
        core = {course.name for course in self.courses if course.relevance is Relevance.CORE}
        detached = sorted(
            course.name
            for course in self.courses
            if course.prerequisite_for is not None and course.prerequisite_for not in core
        )
        if detached:
            raise RecommendationError(
                f"中心に選ばれていない科目を前提にする土台があります: {'、'.join(detached)}"
            )
        recommended_and_unlinked = sorted(counts.keys() & set(self.unlinked))
        if recommended_and_unlinked:
            raise RecommendationError(
                f"外した土台が推薦に入っています: {'、'.join(recommended_and_unlinked)}"
            )


def arrange(
    profile: OccupationProfile, matches: Sequence[CourseMatch], choices: Sequence[CourseChoice]
) -> Recommendation:
    ranked = {match.name: (rank, match) for rank, match in enumerate(matches)}
    _require_candidates((choice.name for choice in choices), ranked)
    core: dict[str, CourseChoice] = {}
    for choice in choices:
        if choice.relevance is Relevance.CORE:
            core.setdefault(choice.name, choice)
    linked: dict[str, CourseChoice] = {}
    for choice in choices:
        if choice.name not in core and choice.prerequisite_for in core:
            linked.setdefault(choice.name, choice)
    chosen = {choice.name for choice in choices}
    group = {relevance: index for index, relevance in enumerate(Relevance)}
    ordered = sorted(
        [*core.values(), *linked.values()],
        key=lambda choice: (group[choice.relevance], ranked[choice.name][0]),
    )
    courses = tuple(
        RecommendedCourse(
            choice.name,
            ranked[choice.name][1].syllabus_code,
            choice.relevance,
            choice.reason,
            choice.prerequisite_for,
        )
        for choice in ordered
    )
    unlinked = tuple(
        name for name in ranked if name in chosen and name not in core and name not in linked
    )
    return Recommendation(profile, courses, tuple(match.name for match in matches), unlinked)
