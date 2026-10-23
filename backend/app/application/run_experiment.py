from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import combinations, count
from math import fsum
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
from app.domain.recommendation import Recommendation, Relevance
from app.domain.roadmap import ALL_SEMESTERS

METRICS = (
    *(f"recall@{cutoff}" for cutoff in RECALL_CUTOFFS),
    "candidate_recall",
    "core_precision",
    "expected_as_core",
    "unrelated",
    "cores",
    "foundations",
)


@dataclass(frozen=True)
class StageSeconds:
    reading: float
    searching: float
    selecting: float

    @property
    def total(self) -> float:
        return self.reading + self.searching + self.selecting


@dataclass(frozen=True)
class Scorecard:
    occupation: str
    repeat: int
    candidates: tuple[str, ...]
    result: SelectionResult


@dataclass(frozen=True)
class Trial:
    occupation: str
    repeat: int
    recommendation: Recommendation
    result: SelectionResult
    usage: dict[str, TokenUsage]
    seconds: StageSeconds

    @property
    def scorecard(self) -> Scorecard:
        return Scorecard(self.occupation, self.repeat, self.recommendation.candidates, self.result)


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
            recommendation,
            selection_result(case, recommendation, judgments),
            usage(),
            StageSeconds(
                self._analyzer.seconds,
                selecting - started - self._analyzer.seconds,
                finished - selecting,
            ),
        )


class Side(Enum):
    BEFORE = "before"
    AFTER = "after"


def interleave(
    before: Iterator[Trial | FailedTrial], after: Iterator[Trial | FailedTrial], cases: int
) -> Iterator[tuple[Side, Trial | FailedTrial]]:
    sides = ((Side.BEFORE, before), (Side.AFTER, after))
    for pair in count():
        repeat, case = divmod(pair, cases)
        for side, outcomes in sides if (repeat + case) % 2 == 0 else sides[::-1]:
            outcome = next(outcomes, None)
            if outcome is None:
                return
            yield side, outcome


@dataclass(frozen=True)
class Spread:
    mean: float
    std: float
    low: float
    high: float


@dataclass(frozen=True)
class Ratio:
    numerator: float
    denominator: float


@dataclass(frozen=True)
class ScoredRun:
    repeats: tuple[tuple[Scorecard, ...], ...]
    complete_repeats: int

    @property
    def cards(self) -> list[Scorecard]:
        return [card for group in self.repeats for card in group]

    @property
    def occupations(self) -> frozenset[str]:
        scored = [frozenset(card.occupation for card in group) for group in self.repeats]
        return frozenset.intersection(*scored) if scored else frozenset()


@dataclass(frozen=True)
class ExperimentSummary:
    trials: int
    failures: int
    complete_repeats: int
    scored_repeats: int
    metrics: dict[str, Spread | None]
    overlap: float | None
    core_overlap: float | None
    usage: dict[str, TokenUsage]
    seconds: StageSeconds


def spread(values: Sequence[float]) -> Spread:
    return Spread(mean(values), stdev(values) if len(values) > 1 else 0.0, min(values), max(values))


def _defined_spread(values: Sequence[float | None]) -> Spread | None:
    defined = [value for value in values if value is not None]
    return spread(defined) if defined else None


def mean_of_defined(values: Iterable[float | None]) -> float | None:
    defined = [value for value in values if value is not None]
    return fsum(defined) / len(defined) if defined else None


def ratios(card: Scorecard) -> dict[str, Ratio]:
    result = card.result
    expected = {course.name for course in result.expected}
    cores = [pick for pick in result.picks if pick.relevance is Relevance.CORE]
    return {
        **{
            f"recall@{cutoff}": Ratio(
                len(expected & set(card.candidates[:cutoff])) / len(expected), 1
            )
            for cutoff in RECALL_CUTOFFS
        },
        "candidate_recall": Ratio(1 - len(result.unsearched) / len(result.expected), 1),
        "core_precision": Ratio(
            sum(1 for pick in cores if pick.judgment is Judgment.EXPECTED), len(cores)
        ),
        "expected_as_core": Ratio(result.expected_as(Relevance.CORE), len(result.expected)),
        "unrelated": Ratio(
            sum(1 for pick in result.picks if pick.judgment is Judgment.UNRELATED),
            len(result.picks),
        ),
        "cores": Ratio(len(cores), 1),
        "foundations": Ratio(len(result.picks) - len(cores), 1),
    }


def pooled(parts: Sequence[Ratio]) -> float | None:
    denominator = sum(part.denominator for part in parts)
    return sum(part.numerator for part in parts) / denominator if denominator else None


def repeat_scores(cards: Sequence[Scorecard]) -> dict[str, float | None]:
    per_card = [ratios(card) for card in cards]
    return {key: pooled([entry[key] for entry in per_card]) for key in METRICS}


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def picked(card: Scorecard) -> set[str]:
    return {pick.name for pick in card.result.picks}


def picked_cores(card: Scorecard) -> set[str]:
    return {pick.name for pick in card.result.picks if pick.relevance is Relevance.CORE}


def overlaps(
    cards: Sequence[Scorecard], names: Callable[[Scorecard], set[str]]
) -> dict[str, float]:
    by_occupation: dict[str, list[set[str]]] = defaultdict(list)
    for card in cards:
        by_occupation[card.occupation].append(names(card))
    return {
        occupation: mean(jaccard(left, right) for left, right in combinations(sets, 2))
        for occupation, sets in by_occupation.items()
        if len(sets) >= 2
    }


def scored_run(cards: Sequence[Scorecard], occupations: int) -> ScoredRun:
    by_repeat: dict[int, list[Scorecard]] = defaultdict(list)
    for card in cards:
        by_repeat[card.repeat].append(card)
    groups = [tuple(group) for group in by_repeat.values()]
    complete = [group for group in groups if len(group) == occupations]
    return ScoredRun(tuple(complete or groups), len(complete))


def summarize(
    outcomes: Sequence[Trial | FailedTrial], cases: Sequence[EvaluationCase]
) -> ExperimentSummary | None:
    trials = [outcome for outcome in outcomes if isinstance(outcome, Trial)]
    if not trials:
        return None
    run = scored_run([trial.scorecard for trial in trials], len(cases))
    scores = [repeat_scores(group) for group in run.repeats]
    usage: dict[str, TokenUsage] = {}
    for outcome in outcomes:
        for model, tokens in outcome.usage.items():
            usage[model] = usage[model] + tokens if model in usage else tokens
    return ExperimentSummary(
        trials=len(outcomes),
        failures=len(outcomes) - len(trials),
        complete_repeats=run.complete_repeats,
        scored_repeats=len(run.repeats),
        metrics={key: _defined_spread([score[key] for score in scores]) for key in METRICS},
        overlap=mean_of_defined(overlaps(run.cards, picked).values()),
        core_overlap=mean_of_defined(overlaps(run.cards, picked_cores).values()),
        usage=dict(sorted(usage.items())),
        seconds=StageSeconds(
            mean(trial.seconds.reading for trial in trials),
            mean(trial.seconds.searching for trial in trials),
            mean(trial.seconds.selecting for trial in trials),
        ),
    )
