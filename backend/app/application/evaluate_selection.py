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


class Judgement(Enum):
    EXPECTED = "期待"
    FOUNDATION = "土台"
    MINORITY = "少数"
    UNRELATED = "関係なし"


def judgement_of(labels: Sequence[str], decision: str | None) -> Judgement:
    if labels.count("core") >= 2 or decision == "core":
        return Judgement.EXPECTED
    if len(labels) >= 2:
        return Judgement.FOUNDATION
    if labels:
        return Judgement.MINORITY
    return Judgement.UNRELATED


class HandwrittenProfiles:
    def __init__(self, dataset: EvaluationDataset) -> None:
        self._skills = {case.occupation: case.skills for case in dataset.cases}

    def analyze(self, occupation: str) -> OccupationProfile:
        return OccupationProfile(occupation, occupation, None, self._skills[occupation])


@dataclass(frozen=True)
class SelectionResult:
    occupation: str
    picks: tuple[tuple[str, Relevance, Judgement], ...]
    expected: tuple[tuple[str, Relevance | None], ...]
    unsearched: tuple[str, ...]

    def count(self, relevance: Relevance, judgement: Judgement) -> int:
        return sum(
            1 for _, picked, judged in self.picks if picked is relevance and judged is judgement
        )

    def expected_as(self, relevance: Relevance | None) -> int:
        return sum(1 for _, picked in self.expected if picked is relevance)


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
        self, dataset: EvaluationDataset, judgements: Mapping[tuple[str, str], Judgement]
    ) -> SelectionReport:
        recommend = RecommendCourses(
            self._search,
            self._courses,
            HandwrittenProfiles(dataset),
            self._selector,
            self._candidate_limit,
        )
        results = []
        for case in dataset.cases:
            expected = {
                course
                for (occupation, course), judged in judgements.items()
                if occupation == case.occupation and judged is Judgement.EXPECTED
            }
            if expected != set(case.expected):
                raise EvaluationError(f"{case.occupation}: 期待する科目が判定と合いません")
            recommendation = recommend.run(
                case.occupation, dataset.year, dataset.department, ALL_GRADES
            )
            picked = {course.name: course.relevance for course in recommendation.courses}
            results.append(
                SelectionResult(
                    case.occupation,
                    tuple(
                        (
                            course.name,
                            course.relevance,
                            judgements.get((case.occupation, course.name), Judgement.UNRELATED),
                        )
                        for course in recommendation.courses
                    ),
                    tuple((name, picked.get(name)) for name in case.expected),
                    tuple(name for name in case.expected if name not in recommendation.candidates),
                )
            )
        return SelectionReport(tuple(results))
