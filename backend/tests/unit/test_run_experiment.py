from collections.abc import Callable, Iterator
from contextlib import contextmanager

import pytest

from app.application.evaluate_search import EvaluationCase, EvaluationDataset
from app.application.evaluate_selection import (
    ExpectedCourse,
    Judgment,
    Judgments,
    Pick,
    SelectionResult,
)
from app.application.ports import CourseSelectionError, TokenUsage
from app.application.run_experiment import (
    FailedTrial,
    RunExperiment,
    Spread,
    StageSeconds,
    Trial,
    jaccard,
    summarize,
)
from app.application.search_courses import SearchCourses
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import (
    CandidateCourse,
    CourseChoice,
    RecommendedCourse,
    Relevance,
)
from tests.fakes import (
    FakeChunkSearch,
    FakeCourseSelector,
    FakeEmbedder,
    FakeOccupationAnalyzer,
    courses_ranked_by,
)

CASE = EvaluationCase("職業", ("甲", "乙", "丙"), ("科目A", "科目D"))
DATASET = EvaluationDataset(2026, "情", (CASE,))
SIMILARITIES = {"科目A": 0.9, "科目B": 0.8, "科目C": 0.7, "科目D": 0.6}
JUDGMENTS = Judgments(
    frozenset(SIMILARITIES),
    {
        ("職業", "科目A"): Judgment.EXPECTED,
        ("職業", "科目B"): Judgment.FOUNDATION,
        ("職業", "科目D"): Judgment.EXPECTED,
    },
)
PROFILE = OccupationProfile("職業", "職業の読み", None, ("スキル1", "スキル2", "スキル3"))
CORE, FOUNDATION = Relevance.CORE, Relevance.FOUNDATION
USAGE = {"gpt-5.4-nano": TokenUsage(input=300, cached=100, output=50)}


class FakeMeter:
    @contextmanager
    def meter(self) -> Iterator[Callable[[], dict[str, TokenUsage]]]:
        yield lambda: USAGE


class Ticks:
    def __init__(self) -> None:
        self.now = -1.0

    def __call__(self) -> float:
        self.now += 1.0
        return self.now


class FailingOnceSelector(FakeCourseSelector):
    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        if not self.calls:
            self.calls.append((profile, candidates))
            raise CourseSelectionError("推薦に使う外部のサービスの呼び出しに失敗しました")
        return super().select(profile, candidates)


def experiment(selector: FakeCourseSelector) -> RunExperiment:
    repository, search = courses_ranked_by(SIMILARITIES)
    return RunExperiment(
        search,
        repository,
        FakeOccupationAnalyzer({"職業": PROFILE}),
        selector,
        3,
        FakeMeter(),
        Ticks(),
    )


def test_each_repeat_runs_the_whole_recommendation_and_keeps_its_cost_and_stage_times() -> None:
    selector = FakeCourseSelector(
        [
            CourseChoice("科目A", CORE, "理由A"),
            CourseChoice("科目C", FOUNDATION, "理由C", "科目A"),
        ]
    )

    outcomes = list(experiment(selector).trials(DATASET, JUDGMENTS, 2))

    assert [outcome.repeat for outcome in outcomes] == [1, 2]
    first = outcomes[0]
    assert isinstance(first, Trial)
    assert first.skills == PROFILE.skills
    assert first.candidates == ("科目A", "科目B", "科目C")
    assert [course.name for course in first.courses] == ["科目A", "科目C"]
    assert first.result.picks == (
        Pick("科目A", CORE, Judgment.EXPECTED),
        Pick("科目C", FOUNDATION, Judgment.UNRELATED),
    )
    assert first.usage == USAGE
    assert first.seconds == StageSeconds(reading=1.0, searching=3.0, selecting=1.0)


def test_a_search_without_hits_ends_the_recommendation_before_selecting() -> None:
    repository, _ = courses_ranked_by(SIMILARITIES)
    search = SearchCourses(repository, FakeChunkSearch([]), FakeEmbedder())
    selector = FakeCourseSelector([CourseChoice("科目A", CORE, "理由A")])
    experiment = RunExperiment(
        search,
        repository,
        FakeOccupationAnalyzer({"職業": PROFILE}),
        selector,
        3,
        FakeMeter(),
        Ticks(),
    )

    [only] = experiment.trials(DATASET, JUDGMENTS, 1)

    assert isinstance(only, Trial)
    assert (only.candidates, only.courses, selector.calls) == ((), (), [])
    assert only.seconds == StageSeconds(reading=1.0, searching=3.0, selecting=0.0)


def test_a_failed_llm_call_keeps_its_usage_and_the_experiment_goes_on() -> None:
    selector = FailingOnceSelector([CourseChoice("科目A", CORE, "理由A")])

    outcomes = list(experiment(selector).trials(DATASET, JUDGMENTS, 2))

    assert outcomes[0] == FailedTrial(
        "職業", 1, "推薦に使う外部のサービスの呼び出しに失敗しました", USAGE
    )
    assert isinstance(outcomes[1], Trial)


def trial(
    occupation: str,
    repeat: int,
    candidates: tuple[str, ...],
    picks: tuple[Pick, ...],
    seconds: float,
) -> Trial:
    picked = {pick.name: pick.relevance for pick in picks}
    return Trial(
        occupation,
        repeat,
        PROFILE.skills,
        candidates,
        tuple(
            RecommendedCourse(
                pick.name,
                "10000",
                pick.relevance,
                "理由",
                None if pick.relevance is CORE else "科目A",
            )
            for pick in picks
        ),
        SelectionResult(
            occupation,
            picks,
            tuple(
                ExpectedCourse(name, picked.get(name), name in candidates, False)
                for name in CASE.expected
            ),
            (),
        ),
        USAGE,
        StageSeconds(seconds, 0.5, seconds),
    )


def test_summary_averages_each_repeat_and_measures_the_spread_and_overlap() -> None:
    first = trial(
        "職業",
        1,
        ("科目A", "科目B", "科目C"),
        (Pick("科目A", CORE, Judgment.EXPECTED), Pick("科目C", FOUNDATION, Judgment.UNRELATED)),
        1.0,
    )
    second = trial(
        "職業",
        2,
        ("科目D", "科目A"),
        (Pick("科目A", CORE, Judgment.EXPECTED), Pick("科目D", CORE, Judgment.EXPECTED)),
        3.0,
    )
    failed = FailedTrial("職業", 3, "失敗", USAGE)

    summary = summarize([first, second, failed], DATASET.cases)

    assert (summary.trials, summary.failures, summary.complete_repeats) == (3, 1, 2)
    assert summary.recall[0] == Spread(mean=0.75, std=0.25, low=0.5, high=1.0)
    assert summary.core_precision == Spread(1.0, 0.0, 1.0, 1.0)
    assert summary.expected_as_core == Spread(0.75, 0.25, 0.5, 1.0)
    assert summary.unrelated == Spread(0.25, 0.25, 0.0, 0.5)
    assert summary.cores == Spread(1.5, 0.5, 1.0, 2.0)
    assert summary.foundations == Spread(0.5, 0.5, 0.0, 1.0)
    assert summary.overlap == pytest.approx(1 / 3)
    assert summary.core_overlap == pytest.approx(1 / 2)
    assert summary.usage == {"gpt-5.4-nano": TokenUsage(900, 300, 150)}
    assert summary.seconds == StageSeconds(2.0, 0.5, 2.0)


def test_a_repeat_cut_short_is_left_out_of_the_scores_but_not_of_the_cost() -> None:
    cases = (CASE, EvaluationCase("別の職業", ("甲", "乙", "丙"), ("科目A",)))
    full = [
        trial("職業", 1, ("科目A",), (Pick("科目A", CORE, Judgment.EXPECTED),), 1.0),
        trial("別の職業", 1, ("科目A",), (Pick("科目A", CORE, Judgment.EXPECTED),), 1.0),
    ]
    cut = trial("職業", 2, ("科目B",), (Pick("科目B", CORE, Judgment.UNRELATED),), 1.0)

    summary = summarize([*full, cut], cases)

    assert summary.complete_repeats == 1
    assert summary.unrelated == Spread(0.0, 0.0, 0.0, 0.0)
    assert summary.usage == {"gpt-5.4-nano": TokenUsage(900, 300, 150)}


def test_a_single_repeat_has_no_overlap_to_measure() -> None:
    only = trial("職業", 1, ("科目A",), (Pick("科目A", CORE, Judgment.EXPECTED),), 1.0)

    summary = summarize([only], DATASET.cases)

    assert (summary.overlap, summary.core_overlap) == (None, None)
    assert summary.recall[0].std == 0.0


def test_nothing_to_summarize_when_every_recommendation_failed() -> None:
    with pytest.raises(ValueError, match="集計できる推薦がありません"):
        summarize([FailedTrial("職業", 1, "失敗", {})], DATASET.cases)


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [({"甲", "乙"}, {"乙", "丙"}, 1 / 3), ({"甲"}, {"甲"}, 1.0), (set(), set(), 1.0)],
    ids=["partly", "same", "both-empty"],
)
def test_jaccard_is_the_shared_part_of_the_union(
    left: set[str], right: set[str], expected: float
) -> None:
    assert jaccard(left, right) == pytest.approx(expected)
