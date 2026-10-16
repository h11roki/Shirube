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
    EXPECTED = "期待"
    FOUNDATION = "土台"
    MINORITY = "少数"
    UNRELATED = "関係なし"


def judgment_of(labels: Sequence[str], decision: str | None) -> Judgment:
    if decision is not None:
        return Judgment.EXPECTED if decision == Relevance.CORE.value else Judgment.FOUNDATION
    if labels.count(Relevance.CORE.value) >= 2:
        return Judgment.EXPECTED
    if len(labels) >= 2:
        return Judgment.FOUNDATION
    if labels:
        return Judgment.MINORITY
    return Judgment.UNRELATED


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
class ExpectedCourse:
    name: str
    picked: Relevance | None
    searched: bool


@dataclass(frozen=True)
class SelectionResult:
    occupation: str
    picks: tuple[Pick, ...]
    expected: tuple[ExpectedCourse, ...]

    def count(self, relevance: Relevance, judgment: Judgment) -> int:
        return sum(
            1 for pick in self.picks if pick.relevance is relevance and pick.judgment is judgment
        )

    def expected_as(self, relevance: Relevance) -> int:
        return sum(1 for course in self.expected if course.picked is relevance)

    @property
    def skipped(self) -> tuple[str, ...]:
        return tuple(
            course.name for course in self.expected if course.searched and course.picked is None
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

    def run(
        self, dataset: EvaluationDataset, judgments: Mapping[tuple[str, str], Judgment]
    ) -> SelectionReport:
        profiles = HandwrittenProfiles(dataset)
        candidates = self._search.candidates(dataset.year, dataset.department, ALL_GRADES)
        dataset.require_courses_in(candidates.names)
        disagreeing = [
            case.occupation
            for case in dataset.cases
            if set(case.expected)
            != {
                course
                for (occupation, course), judged in judgments.items()
                if occupation == case.occupation and judged is Judgment.EXPECTED
            }
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
            picks = tuple(
                Pick(
                    course.name,
                    course.relevance,
                    judgments.get((case.occupation, course.name), Judgment.UNRELATED),
                )
                for course in recommendation.courses
            )
            expected = tuple(
                ExpectedCourse(name, picked.get(name), name in recommendation.candidates)
                for name in case.expected
            )
            results.append(SelectionResult(case.occupation, picks, expected))
        return SelectionReport(tuple(results))
