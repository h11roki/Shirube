from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import Enum
from statistics import fmean

from app.application.evaluate_search import EvaluationError
from app.application.evaluate_selection import Judgment, Judgments
from app.application.judging import JudgingMaterials
from app.application.ports import (
    ClassificationError,
    CourseClassifier,
    CourseOdds,
    CourseRepository,
)
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
class FailedOccupation:
    occupation: str
    reason: str


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
        self.spent_tokens = 0

    def odds(
        self,
        year: int,
        department: str,
        trials: Sequence[SelectorTrial],
        layouts: Sequence[Layout],
    ) -> Iterator[tuple[Layout, OccupationOdds | FailedOccupation]]:
        pages = {
            material.name: material.page
            for material in JudgingMaterials(self._courses).courses(year, department)
        }
        unknown = sorted({name for trial in trials for name in trial.candidates} - pages.keys())
        if unknown:
            raise EvaluationError(f"判定の資料に無い候補があります: {'、'.join(unknown)}")
        syllabi = self._courses.syllabi_of(
            year, {pages[name] for trial in trials for name in trial.candidates}
        )
        offered = [
            [CandidateCourse(name, syllabi[pages[name]]) for name in trial.candidates]
            for trial in trials
        ]
        return (
            (layout, self._classify(trial, candidates, layout))
            for layout in layouts
            for trial, candidates in zip(trials, offered, strict=True)
        )

    def _classify(
        self, trial: SelectorTrial, candidates: list[CandidateCourse], layout: Layout
    ) -> OccupationOdds | FailedOccupation:
        groups = [candidates] if layout is Layout.GROUPED else [[each] for each in candidates]
        parts = []
        for group in groups:
            try:
                part = self._classifier.classify(trial.profile, group)
            except ClassificationError as error:
                self.spent_tokens += error.input_tokens
                return FailedOccupation(trial.occupation, str(error))
            self.spent_tokens += part.input_tokens
            parts.append(part)
        return OccupationOdds(
            trial.occupation,
            tuple(odds for part in parts for odds in part.odds),
            sum(part.input_tokens for part in parts),
        )


def probability(odds: CourseOdds, target: Target) -> float:
    return odds.core if target is Target.CORE else odds.core + odds.foundation


def calibration(
    measured: Sequence[OccupationOdds], judgments: Judgments, target: Target
) -> Calibration:
    outcomes = []
    for occupation in measured:
        for odds in occupation.odds:
            judgment = judgments.of(occupation.occupation, odds.name)
            correct = (
                judgment is Judgment.EXPECTED
                if target is Target.CORE
                else judgment is not Judgment.UNRELATED
            )
            outcomes.append((probability(odds, target), correct))
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
        by_relevance = sorted(
            odds, key=lambda each: (-probability(each, Target.RELEVANT), each.name)
        )
        by_core = sorted(odds, key=lambda each: (-each.core, each.name))
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
