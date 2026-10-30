from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from app.application.evaluate_search import EvaluationDataset, HandwrittenProfiles
from app.application.evaluate_selection import ExpectedCourse, Judgment, SelectionResult
from app.application.run_experiment import Scorecard
from app.application.search_courses import SearchCourses
from app.domain.recommendation import Relevance
from app.domain.roadmap import ALL_SEMESTERS

TOP_COURSES = 10
TOP_OCCUPATIONS = 5


class Fate(Enum):
    CORE = "core"
    FOUNDATION = "foundation"
    UNLINKED = "unlinked"
    SKIPPED = "skipped"
    READING = "reading"
    SEARCH = "search"


LOSSES = (Fate.UNLINKED, Fate.SKIPPED, Fate.READING, Fate.SEARCH)
PLACEMENTS = (Fate.CORE, Fate.FOUNDATION, Fate.UNLINKED)


@dataclass(frozen=True)
class CourseTally:
    name: str
    counts: Mapping[Fate, int]
    occupations: int

    @property
    def total(self) -> int:
        return sum(self.counts.values())


@dataclass(frozen=True)
class ReadingLoss:
    occupation: str
    repeats: tuple[int, ...]
    courses: Mapping[str, int]

    @property
    def total(self) -> int:
        return sum(self.courses.values())


@dataclass(frozen=True)
class ExperimentAnalysis:
    fates: Mapping[Fate, int]
    judgments: Mapping[Fate, Mapping[Judgment, int]]
    missed: tuple[CourseTally, ...]
    unrelated: tuple[CourseTally, ...]
    reading_losses: tuple[ReadingLoss, ...]


def fate_of(course: ExpectedCourse, reference: frozenset[str]) -> Fate:
    if course.picked is Relevance.CORE:
        return Fate.CORE
    if course.picked is Relevance.FOUNDATION:
        return Fate.FOUNDATION
    if course.unlinked:
        return Fate.UNLINKED
    if course.searched:
        return Fate.SKIPPED
    return Fate.READING if course.name in reference else Fate.SEARCH


def placed(result: SelectionResult) -> list[tuple[Fate, str, Judgment]]:
    return [
        (
            Fate.CORE if pick.relevance is Relevance.CORE else Fate.FOUNDATION,
            pick.name,
            pick.judgment,
        )
        for pick in result.picks
    ] + [(Fate.UNLINKED, pick.name, pick.judgment) for pick in result.unlinked]


class _Tallies:
    def __init__(self) -> None:
        self.counts: dict[str, Counter[Fate]] = defaultdict(Counter)
        self.occupations: dict[str, set[str]] = defaultdict(set)

    def add(self, name: str, fate: Fate, occupation: str) -> None:
        self.counts[name][fate] += 1
        self.occupations[name].add(occupation)

    def top(self) -> tuple[CourseTally, ...]:
        tallies = [
            CourseTally(name, dict(counts), len(self.occupations[name]))
            for name, counts in self.counts.items()
        ]
        return tuple(sorted(tallies, key=lambda tally: (-tally.total, tally.name))[:TOP_COURSES])


def analyze(
    cards: Sequence[Scorecard], references: Mapping[str, frozenset[str]]
) -> ExperimentAnalysis:
    fates: Counter[Fate] = Counter()
    judgments: dict[Fate, Counter[Judgment]] = {placement: Counter() for placement in PLACEMENTS}
    missed = _Tallies()
    unrelated = _Tallies()
    reading: dict[str, Counter[str]] = defaultdict(Counter)
    reading_repeats: dict[str, set[int]] = defaultdict(set)
    for card in cards:
        for course in card.result.expected:
            fate = fate_of(course, references[card.occupation])
            fates[fate] += 1
            if fate in LOSSES:
                missed.add(course.name, fate, card.occupation)
            if fate is Fate.READING:
                reading[card.occupation][course.name] += 1
                reading_repeats[card.occupation].add(card.repeat)
        for placement, name, judgment in placed(card.result):
            judgments[placement][judgment] += 1
            if judgment is Judgment.UNRELATED and placement is not Fate.UNLINKED:
                unrelated.add(name, placement, card.occupation)
    losses = [
        ReadingLoss(occupation, tuple(sorted(reading_repeats[occupation])), dict(courses))
        for occupation, courses in reading.items()
    ]
    return ExperimentAnalysis(
        {fate: fates[fate] for fate in Fate},
        {
            placement: {judgment: judgments[placement][judgment] for judgment in Judgment}
            for placement in PLACEMENTS
        },
        missed.top(),
        unrelated.top(),
        tuple(sorted(losses, key=lambda loss: (-loss.total, loss.occupation))[:TOP_OCCUPATIONS]),
    )


class AnalyzeExperiment:
    def __init__(self, search: SearchCourses, candidate_limit: int) -> None:
        self._search = search
        self._candidate_limit = candidate_limit

    def run(self, dataset: EvaluationDataset, cards: Sequence[Scorecard]) -> ExperimentAnalysis:
        candidates = self._search.candidates(dataset.year, dataset.department, ALL_SEMESTERS)
        dataset.require_courses_in(candidates.names)
        profiles = HandwrittenProfiles(dataset)
        rankings = candidates.pick(
            [profiles.analyze(case.occupation) for case in dataset.cases], self._candidate_limit
        )
        references = {
            case.occupation: frozenset(match.name for match in matches)
            for case, matches in zip(dataset.cases, rankings, strict=True)
        }
        return analyze(cards, references)
