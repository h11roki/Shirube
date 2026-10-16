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
    unlinked: tuple[CourseChoice, ...] = ()

    def __post_init__(self) -> None:
        counts = Counter(
            [*(course.name for course in self.courses), *(choice.name for choice in self.unlinked)]
        )
        repeated = sorted(name for name, count in counts.items() if count > 1)
        if repeated:
            raise RecommendationError(f"同じ科目が 2 回入っています: {'、'.join(repeated)}")
        _require_candidates(counts, self.candidates)
        core = {course.name for course in self.courses if course.relevance is Relevance.CORE}
        without_core = sorted(
            course.name
            for course in self.courses
            if course.prerequisite_for is not None and course.prerequisite_for not in core
        )
        if without_core:
            raise RecommendationError(
                f"中心に選ばれていない科目を前提にする土台があります: {'、'.join(without_core)}"
            )


def arrange(
    profile: OccupationProfile, matches: Sequence[CourseMatch], choices: Sequence[CourseChoice]
) -> Recommendation:
    codes = {match.name: match.syllabus_code for match in matches}
    _require_candidates((choice.name for choice in choices), codes)
    pointed = {choice.prerequisite_for for choice in choices if choice.prerequisite_for is not None}
    unknown = sorted(pointed - codes.keys())
    if unknown:
        raise RecommendationError(f"候補に無い科目を前提にしています: {'、'.join(unknown)}")
    core: dict[str, CourseChoice] = {}
    for choice in choices:
        if choice.relevance is Relevance.CORE:
            core.setdefault(choice.name, choice)
    linked: dict[str, CourseChoice] = {}
    unlinked: dict[str, CourseChoice] = {}
    for choice in choices:
        if choice.name in core:
            continue
        if choice.prerequisite_for in core:
            linked.setdefault(choice.name, choice)
        else:
            unlinked.setdefault(choice.name, choice)
    kept = [core[name] for name in codes if name in core] + [
        linked[name] for name in codes if name in linked
    ]
    courses = tuple(
        RecommendedCourse(
            choice.name,
            codes[choice.name],
            choice.relevance,
            choice.reason,
            choice.prerequisite_for,
        )
        for choice in kept
    )
    dropped = tuple(unlinked[name] for name in codes if name in unlinked and name not in linked)
    return Recommendation(profile, courses, tuple(match.name for match in matches), dropped)
