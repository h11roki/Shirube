from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from itertools import combinations
from statistics import mean, stdev
from time import perf_counter

from app.application.build_plans import UPSTREAM_ERRORS
from app.application.evaluate_search import (
    RECALL_CUTOFFS,
    EvaluationCase,
    EvaluationDataset,
    EvaluationError,
)
from app.application.evaluate_selection import (
    Judgment,
    Judgments,
    SelectionResult,
    require_judged,
    selection_result,
)
from app.application.ports import (
    CourseRepository,
    CourseSelector,
    OccupationAnalyzer,
    TokenUsage,
    UsageMeter,
)
from app.application.recommend_courses import RecommendCourses, RecommendStep
from app.application.search_courses import SearchCourses
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import RecommendedCourse, Relevance
from app.domain.roadmap import ALL_SEMESTERS


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
    profile: OccupationProfile
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
        if candidate_limit < max(RECALL_CUTOFFS):
            raise EvaluationError(
                f"候補の数を {max(RECALL_CUTOFFS)} 以上にしてください"
                f"(検索の再現率 @{max(RECALL_CUTOFFS)} を候補から測るため)"
            )
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
            except UPSTREAM_ERRORS as error:
                return FailedTrial(case.occupation, repeat, str(error), usage())
        finished = self._clock()
        selecting = entered.get(RecommendStep.SELECTING, finished)
        return Trial(
            case.occupation,
            repeat,
            recommendation.profile,
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
    candidate_recall: float
    core_precision: float | None
    expected_as_core: float
    unrelated: float | None
    cores: float
    foundations: float


@dataclass(frozen=True)
class ExperimentSummary:
    trials: int
    failures: int
    complete_repeats: int
    scored_repeats: int
    recall: tuple[Spread, ...]
    candidate_recall: Spread
    core_precision: Spread | None
    expected_as_core: Spread
    unrelated: Spread | None
    cores: Spread
    foundations: Spread
    overlap: float | None
    core_overlap: float | None
    usage: dict[str, TokenUsage]
    seconds: StageSeconds


def spread(values: Sequence[float]) -> Spread:
    return Spread(mean(values), stdev(values) if len(values) > 1 else 0.0, min(values), max(values))


def _defined_spread(values: Sequence[float | None]) -> Spread | None:
    defined = [value for value in values if value is not None]
    return spread(defined) if defined else None


def _ratio(part: int, whole: int) -> float | None:
    return part / whole if whole else None


def repeat_scores(trials: Sequence[Trial], cases: Sequence[EvaluationCase]) -> RepeatScores:
    expected_of = {case.occupation: set(case.expected) for case in cases}
    recall = tuple(
        mean(
            len(expected_of[trial.occupation] & set(trial.candidates[:cutoff]))
            / len(expected_of[trial.occupation])
            for trial in trials
        )
        for cutoff in RECALL_CUTOFFS
    )
    picks = [pick for trial in trials for pick in trial.result.picks]
    cores = [pick for pick in picks if pick.relevance is Relevance.CORE]
    return RepeatScores(
        recall,
        mean(1 - len(trial.result.unsearched) / len(trial.result.expected) for trial in trials),
        _ratio(sum(1 for pick in cores if pick.judgment is Judgment.EXPECTED), len(cores)),
        sum(trial.result.expected_as(Relevance.CORE) for trial in trials)
        / sum(len(trial.result.expected) for trial in trials),
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
) -> ExperimentSummary | None:
    trials = [outcome for outcome in outcomes if isinstance(outcome, Trial)]
    if not trials:
        return None
    by_repeat: dict[int, list[Trial]] = defaultdict(list)
    by_occupation: dict[str, list[Trial]] = defaultdict(list)
    for trial in trials:
        by_repeat[trial.repeat].append(trial)
        by_occupation[trial.occupation].append(trial)
    complete = [group for group in by_repeat.values() if len(group) == len(cases)]
    scores = [repeat_scores(group, cases) for group in complete or list(by_repeat.values())]
    usage: dict[str, TokenUsage] = {}
    for outcome in outcomes:
        for model, tokens in outcome.usage.items():
            usage[model] = usage[model] + tokens if model in usage else tokens
    return ExperimentSummary(
        trials=len(outcomes),
        failures=len(outcomes) - len(trials),
        complete_repeats=len(complete),
        scored_repeats=len(scores),
        recall=tuple(
            spread([score.recall[index] for score in scores])
            for index in range(len(RECALL_CUTOFFS))
        ),
        candidate_recall=spread([score.candidate_recall for score in scores]),
        core_precision=_defined_spread([score.core_precision for score in scores]),
        expected_as_core=spread([score.expected_as_core for score in scores]),
        unrelated=_defined_spread([score.unrelated for score in scores]),
        cores=spread([score.cores for score in scores]),
        foundations=spread([score.foundations for score in scores]),
        overlap=overlap(
            [
                [{pick.name for pick in trial.result.picks} for trial in group]
                for group in by_occupation.values()
            ]
        ),
        core_overlap=overlap(
            [
                [
                    {pick.name for pick in trial.result.picks if pick.relevance is Relevance.CORE}
                    for trial in group
                ]
                for group in by_occupation.values()
            ]
        ),
        usage=dict(sorted(usage.items())),
        seconds=StageSeconds(
            mean(trial.seconds.reading for trial in trials),
            mean(trial.seconds.searching for trial in trials),
            mean(trial.seconds.selecting for trial in trials),
        ),
    )
