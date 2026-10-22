from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from itertools import combinations
from statistics import mean, pstdev
from time import perf_counter

from app.application.evaluate_search import EvaluationCase, EvaluationDataset
from app.application.evaluate_selection import (
    Judgment,
    Judgments,
    SelectionResult,
    require_judged,
    selection_result,
)
from app.application.ports import (
    CourseRepository,
    CourseSelectionError,
    CourseSelector,
    OccupationAnalysisError,
    OccupationAnalyzer,
    TokenUsage,
    UsageMeter,
)
from app.application.recommend_courses import RecommendCourses, RecommendStep
from app.application.search_courses import SearchCourses
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import RecommendedCourse, Relevance
from app.domain.roadmap import ALL_SEMESTERS

RECALL_DEPTHS = (10, 20, 30)


@dataclass(frozen=True)
class StageSeconds:
    reading: float
    searching: float
    selecting: float

    @property
    def total(self) -> float:
        return self.reading + self.searching + self.selecting


@dataclass(frozen=True)
class Trial:
    occupation: str
    repeat: int
    skills: tuple[str, ...]
    candidates: tuple[str, ...]
    courses: tuple[RecommendedCourse, ...]
    result: SelectionResult
    usage: dict[str, TokenUsage]
    seconds: StageSeconds


@dataclass(frozen=True)
class FailedTrial:
    occupation: str
    repeat: int
    failure: str
    usage: dict[str, TokenUsage]


class _TimedAnalyzer:
    def __init__(self, analyzer: OccupationAnalyzer, clock: Callable[[], float]) -> None:
        self._analyzer = analyzer
        self._clock = clock
        self.seconds = 0.0

    def analyze(self, occupation: str) -> OccupationProfile:
        started = self._clock()
        try:
            return self._analyzer.analyze(occupation)
        finally:
            self.seconds = self._clock() - started


class RunExperiment:
    def __init__(
        self,
        search: SearchCourses,
        courses: CourseRepository,
        analyzer: OccupationAnalyzer,
        selector: CourseSelector,
        candidate_limit: int,
        meter: UsageMeter,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._search = search
        self._analyzer = _TimedAnalyzer(analyzer, clock)
        self._recommend = RecommendCourses(
            search, courses, self._analyzer, selector, candidate_limit
        )
        self._meter = meter
        self._clock = clock

    def trials(
        self, dataset: EvaluationDataset, judgments: Judgments, repeats: int
    ) -> Iterator[Trial | FailedTrial]:
        candidates = self._search.candidates(dataset.year, dataset.department, ALL_SEMESTERS)
        require_judged(dataset, judgments, candidates.names)
        for repeat in range(1, repeats + 1):
            for case in dataset.cases:
                yield self._trial(dataset, judgments, case, repeat)

    def _trial(
        self, dataset: EvaluationDataset, judgments: Judgments, case: EvaluationCase, repeat: int
    ) -> Trial | FailedTrial:
        entered: dict[RecommendStep, float] = {}

        def mark(step: RecommendStep) -> None:
            entered[step] = self._clock()

        started = self._clock()
        with self._meter.meter() as usage:
            try:
                recommendation = self._recommend.run(
                    case.occupation, dataset.year, dataset.department, ALL_SEMESTERS, enter=mark
                )
            except (OccupationAnalysisError, CourseSelectionError) as error:
                return FailedTrial(case.occupation, repeat, str(error), usage())
        finished = self._clock()
        selecting = entered.get(RecommendStep.SELECTING, finished)
        return Trial(
            case.occupation,
            repeat,
            recommendation.profile.skills,
            recommendation.candidates,
            recommendation.courses,
            selection_result(case, recommendation, judgments),
            usage(),
            StageSeconds(
                self._analyzer.seconds,
                selecting - started - self._analyzer.seconds,
                finished - selecting,
            ),
        )


@dataclass(frozen=True)
class Spread:
    mean: float
    std: float
    low: float
    high: float


@dataclass(frozen=True)
class RepeatScores:
    recall: tuple[float, ...]
    core_precision: float
    expected_as_core: float
    unrelated: float
    cores: float
    foundations: float


@dataclass(frozen=True)
class ExperimentSummary:
    trials: int
    failures: int
    complete_repeats: int
    recall: tuple[Spread, ...]
    core_precision: Spread
    expected_as_core: Spread
    unrelated: Spread
    cores: Spread
    foundations: Spread
    overlap: float | None
    core_overlap: float | None
    usage: dict[str, TokenUsage]
    seconds: StageSeconds


def spread(values: Sequence[float]) -> Spread:
    return Spread(mean(values), pstdev(values), min(values), max(values))


def _ratio(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def repeat_scores(trials: Sequence[Trial], cases: Sequence[EvaluationCase]) -> RepeatScores:
    expected_of = {case.occupation: set(case.expected) for case in cases}
    recall = tuple(
        mean(
            len(expected_of[trial.occupation] & set(trial.candidates[:depth]))
            / len(expected_of[trial.occupation])
            for trial in trials
        )
        for depth in RECALL_DEPTHS
    )
    picks = [pick for trial in trials for pick in trial.result.picks]
    cores = [pick for pick in picks if pick.relevance is Relevance.CORE]
    expected = sum(len(trial.result.expected) for trial in trials)
    return RepeatScores(
        recall,
        _ratio(sum(1 for pick in cores if pick.judgment is Judgment.EXPECTED), len(cores)),
        _ratio(sum(trial.result.expected_as(Relevance.CORE) for trial in trials), expected),
        _ratio(sum(1 for pick in picks if pick.judgment is Judgment.UNRELATED), len(picks)),
        len(cores) / len(trials),
        (len(picks) - len(cores)) / len(trials),
    )


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def overlap(groups: Sequence[Sequence[set[str]]]) -> float | None:
    within = [
        mean(jaccard(left, right) for left, right in combinations(sets, 2))
        for sets in groups
        if len(sets) >= 2
    ]
    return mean(within) if within else None


def summarize(
    outcomes: Sequence[Trial | FailedTrial], cases: Sequence[EvaluationCase]
) -> ExperimentSummary:
    trials = [outcome for outcome in outcomes if isinstance(outcome, Trial)]
    if not trials:
        raise ValueError("集計できる推薦がありません")
    by_repeat: dict[int, list[Trial]] = defaultdict(list)
    by_occupation: dict[str, list[Trial]] = defaultdict(list)
    for trial in trials:
        by_repeat[trial.repeat].append(trial)
        by_occupation[trial.occupation].append(trial)
    complete = {repeat: group for repeat, group in by_repeat.items() if len(group) == len(cases)}
    scores = [repeat_scores(group, cases) for group in (complete or by_repeat).values()]
    usage: Counter[tuple[str, str]] = Counter()
    for outcome in outcomes:
        for model, tokens in outcome.usage.items():
            usage[(model, "input")] += tokens.input
            usage[(model, "cached")] += tokens.cached
            usage[(model, "output")] += tokens.output
    return ExperimentSummary(
        len(outcomes),
        len(outcomes) - len(trials),
        len(complete),
        tuple(
            spread([score.recall[index] for score in scores]) for index in range(len(RECALL_DEPTHS))
        ),
        spread([score.core_precision for score in scores]),
        spread([score.expected_as_core for score in scores]),
        spread([score.unrelated for score in scores]),
        spread([score.cores for score in scores]),
        spread([score.foundations for score in scores]),
        overlap(
            [
                [{pick.name for pick in trial.result.picks} for trial in group]
                for group in by_occupation.values()
            ]
        ),
        overlap(
            [
                [
                    {pick.name for pick in trial.result.picks if pick.relevance is Relevance.CORE}
                    for trial in group
                ]
                for group in by_occupation.values()
            ]
        ),
        {
            model: TokenUsage(
                usage[(model, "input")], usage[(model, "cached")], usage[(model, "output")]
            )
            for model in sorted({model for model, _ in usage})
        },
        StageSeconds(
            mean(trial.seconds.reading for trial in trials),
            mean(trial.seconds.searching for trial in trials),
            mean(trial.seconds.selecting for trial in trials),
        ),
    )
