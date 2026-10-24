from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import astuple
from math import sqrt

import pytest

from app.application.evaluate_search import EvaluationCase, EvaluationDataset, EvaluationError
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
    Side,
    Spread,
    StageSeconds,
    Trial,
    interleave,
    jaccard,
    summarize,
)
from app.application.search_courses import SearchCourses
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import (
    CandidateCourse,
    CourseChoice,
    Recommendation,
    RecommendedCourse,
    Relevance,
)
from tests.fakes import (
    FakeChunkSearch,
    FakeCourseRepository,
    FakeCourseSelector,
    FakeEmbedder,
    FakeOccupationAnalyzer,
    courses_ranked_by,
)

CASE = EvaluationCase("職業", ("甲", "乙", "丙"), ("科目A", "科目D"))
OTHER = EvaluationCase("別の職業", ("甲", "乙", "丙"), ("科目A",))
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
LIMIT = 20
HALF_APART = sqrt(0.125)


class FakeMeter:
    @contextmanager
    def meter(self) -> Iterator[Callable[[], dict[str, TokenUsage]]]:
        yield lambda: USAGE


class CountingMeter:
    def __init__(self) -> None:
        self.opened = 0

    @contextmanager
    def meter(self) -> Iterator[Callable[[], dict[str, TokenUsage]]]:
        self.opened += 1
        usage = {"gpt-5.4-nano": TokenUsage(self.opened, 0, 0)}
        yield lambda: usage


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


def experiment(
    selector: FakeCourseSelector,
    ranked: tuple[FakeCourseRepository, SearchCourses] | None = None,
    candidate_limit: int = LIMIT,
) -> RunExperiment:
    repository, search = ranked or courses_ranked_by(SIMILARITIES)
    return RunExperiment(
        search,
        repository,
        FakeOccupationAnalyzer({"職業": PROFILE}),
        selector,
        candidate_limit,
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
    assert first.recommendation.profile == PROFILE
    assert first.recommendation.candidates == ("科目A", "科目B", "科目C", "科目D")
    assert [course.name for course in first.recommendation.courses] == ["科目A", "科目C"]
    assert first.result.picks == (
        Pick("科目A", CORE, Judgment.EXPECTED),
        Pick("科目C", FOUNDATION, Judgment.UNRELATED),
    )
    assert first.usage == USAGE
    assert first.seconds == StageSeconds(reading=1.0, searching=3.0, selecting=1.0)


def test_each_recommendation_keeps_only_the_usage_of_its_own_calls() -> None:
    repository, search = courses_ranked_by(SIMILARITIES)
    experiment = RunExperiment(
        search,
        repository,
        FakeOccupationAnalyzer({"職業": PROFILE}),
        FakeCourseSelector([CourseChoice("科目A", CORE, "理由A")]),
        LIMIT,
        CountingMeter(),
        Ticks(),
    )

    outcomes = list(experiment.trials(DATASET, JUDGMENTS, 2))

    assert [outcome.usage for outcome in outcomes] == [
        {"gpt-5.4-nano": TokenUsage(1, 0, 0)},
        {"gpt-5.4-nano": TokenUsage(2, 0, 0)},
    ]


def test_a_failed_llm_call_keeps_its_usage_and_the_experiment_goes_on() -> None:
    selector = FailingOnceSelector([CourseChoice("科目A", CORE, "理由A")])

    outcomes = list(experiment(selector).trials(DATASET, JUDGMENTS, 2))

    assert outcomes[0] == FailedTrial(
        "職業", 1, "推薦に使う外部のサービスの呼び出しに失敗しました", USAGE
    )
    assert isinstance(outcomes[1], Trial)


def test_a_failed_embedding_fails_only_that_recommendation_as_in_production() -> None:
    selector = FakeCourseSelector([CourseChoice("科目A", CORE, "理由A")])
    ranked = courses_ranked_by(SIMILARITIES, FakeEmbedder(failing_call=1))

    outcomes = list(experiment(selector, ranked).trials(DATASET, JUDGMENTS, 2))

    assert outcomes[0] == FailedTrial(
        "職業", 1, "埋め込みの API 呼び出しに失敗しました: 応答が無い", USAGE
    )
    assert isinstance(outcomes[1], Trial)


def test_a_search_without_hits_ends_the_recommendation_before_selecting() -> None:
    repository, _ = courses_ranked_by(SIMILARITIES)
    search = SearchCourses(repository, FakeChunkSearch([]), FakeEmbedder(), by_skill=True)
    selector = FakeCourseSelector([CourseChoice("科目A", CORE, "理由A")])

    [only] = experiment(selector, (repository, search)).trials(DATASET, JUDGMENTS, 1)

    assert isinstance(only, Trial)
    assert (only.recommendation.candidates, only.recommendation.courses) == ((), ())
    assert selector.calls == []
    assert only.seconds == StageSeconds(reading=1.0, searching=3.0, selecting=0.0)


def test_candidates_fewer_than_the_deepest_recall_cutoff_are_refused() -> None:
    with pytest.raises(EvaluationError, match="候補の数を 20 以上にしてください"):
        experiment(FakeCourseSelector([]), candidate_limit=19)


def trial(
    case: EvaluationCase,
    repeat: int,
    candidates: tuple[str, ...],
    picks: tuple[Pick, ...],
    seconds: float,
) -> Trial:
    picked = {pick.name: pick.relevance for pick in picks}
    return Trial(
        case.occupation,
        repeat,
        Recommendation(
            PROFILE,
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
            candidates,
        ),
        SelectionResult(
            case.occupation,
            picks,
            tuple(
                ExpectedCourse(name, picked.get(name), name in candidates, False)
                for name in case.expected
            ),
            (),
        ),
        USAGE,
        StageSeconds(seconds, 0.5, seconds),
    )


def values(spread: Spread | None) -> tuple[float, ...] | None:
    return None if spread is None else astuple(spread)


def test_summary_averages_each_repeat_and_measures_the_spread_and_overlap() -> None:
    first = trial(
        CASE,
        1,
        ("科目A", "科目B", "科目C"),
        (Pick("科目A", CORE, Judgment.EXPECTED), Pick("科目C", FOUNDATION, Judgment.UNRELATED)),
        1.0,
    )
    second = trial(
        CASE,
        2,
        ("科目D", "科目A"),
        (Pick("科目A", CORE, Judgment.EXPECTED), Pick("科目D", CORE, Judgment.EXPECTED)),
        3.0,
    )
    failed = FailedTrial("職業", 3, "失敗", USAGE)

    summary = summarize([first, second, failed], DATASET.cases)

    assert summary is not None
    assert (summary.trials, summary.failures) == (3, 1)
    assert (summary.complete_repeats, summary.scored_repeats) == (2, 2)
    halves = pytest.approx((0.75, HALF_APART, 0.5, 1.0))
    assert {key: values(spread) for key, spread in summary.metrics.items()} == {
        "recall@10": halves,
        "recall@20": halves,
        "candidate_recall": halves,
        "core_precision": (1.0, 0.0, 1.0, 1.0),
        "expected_as_core": halves,
        "unrelated": pytest.approx((0.25, HALF_APART, 0.0, 0.5)),
        "cores": pytest.approx((1.5, 2 * HALF_APART, 1.0, 2.0)),
        "foundations": pytest.approx((0.5, 2 * HALF_APART, 0.0, 1.0)),
    }
    assert summary.overlap == pytest.approx(1 / 3)
    assert summary.core_overlap == pytest.approx(1 / 2)
    assert summary.usage == {"gpt-5.4-nano": TokenUsage(900, 300, 150)}
    assert summary.seconds == StageSeconds(2.0, 0.5, 2.0)


def test_a_repeat_cut_short_is_left_out_of_the_scores_but_not_of_the_cost() -> None:
    full = [
        trial(CASE, 1, ("科目A",), (Pick("科目A", CORE, Judgment.EXPECTED),), 1.0),
        trial(OTHER, 1, ("科目A",), (Pick("科目A", CORE, Judgment.EXPECTED),), 1.0),
    ]
    cut = trial(CASE, 2, ("科目B",), (Pick("科目B", CORE, Judgment.UNRELATED),), 1.0)

    summary = summarize([*full, cut], (CASE, OTHER))

    assert summary is not None
    assert (summary.complete_repeats, summary.scored_repeats) == (1, 1)
    assert values(summary.metrics["unrelated"]) == (0.0, 0.0, 0.0, 0.0)
    assert summary.usage == {"gpt-5.4-nano": TokenUsage(900, 300, 150)}


def test_the_overlap_also_leaves_out_a_repeat_cut_short() -> None:
    full = [
        trial(case, repeat, ("科目A",), (Pick("科目A", CORE, Judgment.EXPECTED),), 1.0)
        for repeat in (1, 2)
        for case in (CASE, OTHER)
    ]
    cut = trial(CASE, 3, ("科目B",), (Pick("科目B", CORE, Judgment.UNRELATED),), 1.0)

    summary = summarize([*full, cut], (CASE, OTHER))

    assert summary is not None
    assert (summary.overlap, summary.core_overlap) == (1.0, 1.0)


def test_without_a_complete_repeat_the_scores_come_from_the_repeats_cut_short() -> None:
    cut = trial(CASE, 1, ("科目B",), (Pick("科目B", CORE, Judgment.UNRELATED),), 1.0)

    summary = summarize([cut], (CASE, OTHER))

    assert summary is not None
    assert (summary.complete_repeats, summary.scored_repeats) == (0, 1)
    assert values(summary.metrics["unrelated"]) == (1.0, 0.0, 1.0, 1.0)


def test_shares_of_nothing_picked_are_left_undefined_rather_than_zero() -> None:
    empty = trial(CASE, 1, ("科目A",), (), 1.0)

    summary = summarize([empty], DATASET.cases)

    assert summary is not None
    assert (summary.metrics["core_precision"], summary.metrics["unrelated"]) == (None, None)
    assert values(summary.metrics["expected_as_core"]) == (0.0, 0.0, 0.0, 0.0)
    assert values(summary.metrics["cores"]) == (0.0, 0.0, 0.0, 0.0)


def test_candidate_recall_counts_expected_courses_searched_but_not_picked() -> None:
    only = trial(CASE, 1, ("科目A", "科目D"), (Pick("科目A", CORE, Judgment.EXPECTED),), 1.0)

    summary = summarize([only], DATASET.cases)

    assert summary is not None
    assert values(summary.metrics["candidate_recall"]) == (1.0, 0.0, 1.0, 1.0)
    assert values(summary.metrics["expected_as_core"]) == (0.5, 0.0, 0.5, 0.5)


def test_a_single_repeat_has_no_overlap_to_measure() -> None:
    only = trial(CASE, 1, ("科目A",), (Pick("科目A", CORE, Judgment.EXPECTED),), 1.0)

    summary = summarize([only], DATASET.cases)

    assert summary is not None
    assert (summary.overlap, summary.core_overlap) == (None, None)
    assert values(summary.metrics["recall@10"]) == (0.5, 0.0, 0.5, 0.5)


def test_nothing_is_summarized_when_every_recommendation_failed() -> None:
    assert summarize([FailedTrial("職業", 1, "失敗", USAGE)], DATASET.cases) is None


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [({"甲", "乙"}, {"乙", "丙"}, 1 / 3), ({"甲"}, {"甲"}, 1.0), (set(), set(), 1.0)],
    ids=["partly", "same", "both-empty"],
)
def test_jaccard_is_the_shared_part_of_the_union(
    left: set[str], right: set[str], expected: float
) -> None:
    assert jaccard(left, right) == pytest.approx(expected)


def test_interleaving_runs_one_at_a_time_and_each_occupation_alternates_the_side_first() -> None:
    started: list[str] = []

    def outcomes(side: str) -> Iterator[Trial | FailedTrial]:
        for repeat in (1, 2):
            for occupation in ("職業A", "職業B"):
                started.append(side)
                yield FailedTrial(occupation, repeat, side, USAGE)

    pairs = interleave(outcomes("前"), outcomes("後"), cases=2)
    first = next(pairs)

    assert started == ["前"]
    assert [(outcome.occupation, outcome.repeat, side) for side, outcome in (first, *pairs)] == [
        ("職業A", 1, Side.BEFORE),
        ("職業A", 1, Side.AFTER),
        ("職業B", 1, Side.AFTER),
        ("職業B", 1, Side.BEFORE),
        ("職業A", 2, Side.AFTER),
        ("職業A", 2, Side.BEFORE),
        ("職業B", 2, Side.BEFORE),
        ("職業B", 2, Side.AFTER),
    ]
    assert started == ["前", "後", "後", "前", "後", "前", "前", "後"]
