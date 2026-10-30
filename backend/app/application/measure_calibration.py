from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import Enum
from statistics import fmean

from app.application.evaluate_search import EvaluationError
from app.application.evaluate_selection import Judgment, Judgments
from app.application.judging import JudgingMaterials
from app.application.ports import CourseClassifier, CourseOdds, CourseRepository
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse, Relevance

BINS = 10


class Layout(Enum):
    GROUPED = "grouped"
    SEPARATE = "separate"


class Target(Enum):
    CORE = "core"
    RELEVANT = "relevant"


@dataclass(frozen=True)
class SelectorTrial:
    occupation: str
    profile: OccupationProfile
    candidates: tuple[str, ...]
    picks: tuple[tuple[str, Relevance], ...]


@dataclass(frozen=True)
class OccupationOdds:
    occupation: str
    odds: tuple[CourseOdds, ...]
    input_tokens: int


@dataclass(frozen=True)
class Bin:
    low: float
    high: float
    count: int
    mean_probability: float
    hit_rate: float


@dataclass(frozen=True)
class Calibration:
    count: int
    ece: float
    brier: float
    bins: tuple[Bin, ...]


@dataclass(frozen=True)
class Choices:
    picked: int
    unrelated: int
    expected_picked: int
    expected: int
    cores: int
    expected_cores: int


@dataclass(frozen=True)
class Matched:
    occupations: int
    selector: Choices
    classifier: Choices


class MeasureCalibration:
    def __init__(self, courses: CourseRepository, classifier: CourseClassifier) -> None:
        self._courses = courses
        self._classifier = classifier

    def odds(
        self, year: int, department: str, trials: Sequence[SelectorTrial], layout: Layout
    ) -> Iterator[OccupationOdds]:
        pages = {
            material.name: material.page
            for material in JudgingMaterials(self._courses).courses(year, department)
        }
        unknown = sorted({name for trial in trials for name in trial.candidates} - pages.keys())
        if unknown:
            raise EvaluationError(f"判定の資料に無い候補があります: {'、'.join(unknown)}")
        syllabi = self._courses.syllabi_of(year, set(pages.values()))
        return (
            self._classify(
                trial,
                [CandidateCourse(name, syllabi[pages[name]]) for name in trial.candidates],
                layout,
            )
            for trial in trials
        )

    def _classify(
        self, trial: SelectorTrial, candidates: list[CandidateCourse], layout: Layout
    ) -> OccupationOdds:
        if layout is Layout.GROUPED:
            classification = self._classifier.classify(trial.profile, candidates)
            return OccupationOdds(
                trial.occupation, classification.odds, classification.input_tokens
            )
        parts = [self._classifier.classify(trial.profile, [candidate]) for candidate in candidates]
        return OccupationOdds(
            trial.occupation,
            tuple(odds for part in parts for odds in part.odds),
            sum(part.input_tokens for part in parts),
        )


def probability(odds: CourseOdds, target: Target) -> float:
    return odds.core if target is Target.CORE else odds.core + odds.foundation


def hit(judgment: Judgment, target: Target) -> bool:
    if target is Target.CORE:
        return judgment is Judgment.EXPECTED
    return judgment is not Judgment.UNRELATED


def calibration(
    measured: Sequence[OccupationOdds], judgments: Judgments, target: Target
) -> Calibration:
    outcomes = [
        (
            probability(odds, target),
            hit(judgments.of(occupation.occupation, odds.name), target),
        )
        for occupation in measured
        for odds in occupation.odds
    ]
    grouped: list[list[tuple[float, bool]]] = [[] for _ in range(BINS)]
    for chance, correct in outcomes:
        grouped[min(int(chance * BINS), BINS - 1)].append((chance, correct))
    bins = tuple(
        Bin(
            index / BINS,
            (index + 1) / BINS,
            len(inside),
            fmean(chance for chance, _ in inside),
            fmean(correct for _, correct in inside),
        )
        for index, inside in enumerate(grouped)
        if inside
    )
    return Calibration(
        len(outcomes),
        sum(
            part.count / len(outcomes) * abs(part.mean_probability - part.hit_rate) for part in bins
        ),
        fmean((chance - correct) ** 2 for chance, correct in outcomes),
        bins,
    )


def _choices(
    occupation: str,
    candidates: Sequence[str],
    picked: Sequence[str],
    cores: Sequence[str],
    judgments: Judgments,
) -> Choices:
    def judged(name: str) -> Judgment:
        return judgments.of(occupation, name)

    return Choices(
        len(picked),
        sum(1 for name in picked if judged(name) is Judgment.UNRELATED),
        sum(1 for name in picked if judged(name) is Judgment.EXPECTED),
        sum(1 for name in candidates if judged(name) is Judgment.EXPECTED),
        len(cores),
        sum(1 for name in cores if judged(name) is Judgment.EXPECTED),
    )


def _total(parts: Sequence[Choices]) -> Choices:
    return Choices(
        sum(part.picked for part in parts),
        sum(part.unrelated for part in parts),
        sum(part.expected_picked for part in parts),
        sum(part.expected for part in parts),
        sum(part.cores for part in parts),
        sum(part.expected_cores for part in parts),
    )


def matched(
    trials: Sequence[SelectorTrial], measured: Sequence[OccupationOdds], judgments: Judgments
) -> Matched:
    odds_of = {occupation.occupation: occupation.odds for occupation in measured}
    compared = [trial for trial in trials if trial.occupation in odds_of]
    selector: list[Choices] = []
    classifier: list[Choices] = []
    for trial in compared:
        cores = [name for name, relevance in trial.picks if relevance is Relevance.CORE]
        selector.append(
            _choices(
                trial.occupation,
                trial.candidates,
                [name for name, _ in trial.picks],
                cores,
                judgments,
            )
        )
        odds = odds_of[trial.occupation]
        by_relevance = sorted(odds, key=lambda each: -probability(each, Target.RELEVANT))
        by_core = sorted(odds, key=lambda each: -each.core)
        classifier.append(
            _choices(
                trial.occupation,
                trial.candidates,
                [each.name for each in by_relevance[: len(trial.picks)]],
                [each.name for each in by_core[: len(cores)]],
                judgments,
            )
        )
    return Matched(len(compared), _total(selector), _total(classifier))
