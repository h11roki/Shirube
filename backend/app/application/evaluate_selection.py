from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from app.application.evaluate_search import EvaluationDataset, EvaluationError
from app.application.ports import CourseRepository, CourseSelector
from app.application.recommend_courses import RecommendCourses
from app.application.search_courses import SearchCourses
from app.domain.course import ALL_GRADES
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import Relevance


class Judgment(Enum):
    EXPECTED = "expected"
    FOUNDATION = "foundation"
    MINORITY = "minority"
    UNRELATED = "unrelated"


def judgment_of(votes: Sequence[Relevance], decision: Relevance | None) -> Judgment:
    if decision is not None:
        return Judgment.EXPECTED if decision is Relevance.CORE else Judgment.FOUNDATION
    if votes.count(Relevance.CORE) >= 2:
        return Judgment.EXPECTED
    if len(votes) >= 2:
        return Judgment.FOUNDATION
    if votes:
        return Judgment.MINORITY
    return Judgment.UNRELATED


@dataclass(frozen=True)
class Judgments:
    courses: frozenset[str]
    by_course: Mapping[tuple[str, str], Judgment]

    def of(self, occupation: str, course: str) -> Judgment:
        return self.by_course.get((occupation, course), Judgment.UNRELATED)


class HandwrittenProfiles:
    def __init__(self, dataset: EvaluationDataset) -> None:
        self._profiles = {
            case.occupation: OccupationProfile(case.occupation, case.occupation, None, case.skills)
            for case in dataset.cases
        }

    def analyze(self, occupation: str) -> OccupationProfile:
        return self._profiles[occupation]


@dataclass(frozen=True)
class Pick:
    name: str
    relevance: Relevance
    judgment: Judgment


@dataclass(frozen=True)
class UnlinkedPick:
    name: str
    prerequisite_for: str | None
    judgment: Judgment


@dataclass(frozen=True)
class ExpectedCourse:
    name: str
    picked: Relevance | None
    searched: bool
    unlinked: bool


@dataclass(frozen=True)
class SelectionResult:
    occupation: str
    picks: tuple[Pick, ...]
    expected: tuple[ExpectedCourse, ...]
    unlinked: tuple[UnlinkedPick, ...]

    def expected_as(self, relevance: Relevance) -> int:
        return sum(1 for course in self.expected if course.picked is relevance)

    @property
    def expected_unlinked(self) -> tuple[str, ...]:
        return tuple(course.name for course in self.expected if course.unlinked)

    @property
    def skipped(self) -> tuple[str, ...]:
        return tuple(
            course.name
            for course in self.expected
            if course.searched and course.picked is None and not course.unlinked
        )

    @property
    def unsearched(self) -> tuple[str, ...]:
        return tuple(course.name for course in self.expected if not course.searched)


@dataclass(frozen=True)
class SelectionReport:
    results: tuple[SelectionResult, ...]


class EvaluateSelection:
    def __init__(
        self,
        search: SearchCourses,
        courses: CourseRepository,
        selector: CourseSelector,
        candidate_limit: int,
    ) -> None:
        self._search = search
        self._courses = courses
        self._selector = selector
        self._candidate_limit = candidate_limit

    def run(self, dataset: EvaluationDataset, judgments: Judgments) -> SelectionReport:
        profiles = HandwrittenProfiles(dataset)
        candidates = self._search.candidates(dataset.year, dataset.department, ALL_GRADES)
        dataset.require_courses_in(candidates.names)
        unjudged = sorted(candidates.names - judgments.courses)
        if unjudged:
            raise EvaluationError(f"判定していない候補があります: {'、'.join(unjudged)}")
        expected_of: dict[str, set[str]] = defaultdict(set)
        for (occupation, course), judged in judgments.by_course.items():
            if judged is Judgment.EXPECTED:
                expected_of[occupation].add(course)
        disagreeing = [
            case.occupation
            for case in dataset.cases
            if set(case.expected) != expected_of[case.occupation]
        ]
        if disagreeing:
            raise EvaluationError(f"期待する科目が判定と合いません: {'、'.join(disagreeing)}")
        recommend = RecommendCourses(
            self._search, self._courses, profiles, self._selector, self._candidate_limit
        )
        results = []
        for case in dataset.cases:
            recommendation = recommend.run(
                case.occupation, dataset.year, dataset.department, ALL_GRADES
            )
            picked = {course.name: course.relevance for course in recommendation.courses}
            dropped = {choice.name for choice in recommendation.unlinked}
            picks = tuple(
                Pick(course.name, course.relevance, judgments.of(case.occupation, course.name))
                for course in recommendation.courses
            )
            expected = tuple(
                ExpectedCourse(
                    name,
                    picked=picked.get(name),
                    searched=name in recommendation.candidates,
                    unlinked=name in dropped,
                )
                for name in case.expected
            )
            unlinked = tuple(
                UnlinkedPick(
                    choice.name,
                    choice.prerequisite_for,
                    judgments.of(case.occupation, choice.name),
                )
                for choice in recommendation.unlinked
            )
            results.append(SelectionResult(case.occupation, picks, expected, unlinked))
        return SelectionReport(tuple(results))
