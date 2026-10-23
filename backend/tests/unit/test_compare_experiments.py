from collections.abc import Sequence

import pytest

from app.application.compare_experiments import (
    MIN_OCCUPATIONS,
    Change,
    Comparison,
    Interval,
    compare_experiments,
)
from app.application.evaluate_selection import ExpectedCourse, Judgment, Pick, SelectionResult
from app.application.run_experiment import Scorecard, scored_run
from app.domain.recommendation import Relevance

OCCUPATIONS = tuple(f"職業{index}" for index in range(MIN_OCCUPATIONS))
EXPECTED, UNRELATED = Judgment.EXPECTED, Judgment.UNRELATED
ONLY_EXPECTED = (("科目A", EXPECTED),)
WITH_UNRELATED = (("科目A", EXPECTED), ("科目B", UNRELATED))
METRICS = {
    "recall@10",
    "recall@20",
    "candidate_recall",
    "core_precision",
    "expected_as_core",
    "unrelated",
    "cores",
    "foundations",
}


def card(occupation: str, repeat: int, picks: Sequence[tuple[str, Judgment]]) -> Scorecard:
    names = {name for name, _ in picks}
    return Scorecard(
        occupation,
        repeat,
        ("科目A",),
        SelectionResult(
            occupation,
            tuple(Pick(name, Relevance.CORE, judgment) for name, judgment in picks),
            (ExpectedCourse("科目A", Relevance.CORE if "科目A" in names else None, True, False),),
            (),
        ),
    )


def compared(before: Sequence[Scorecard], after: Sequence[Scorecard]) -> Comparison:
    return compare_experiments(
        scored_run(before, len({card.occupation for card in before})),
        scored_run(after, len({card.occupation for card in after})),
        resamples=1_000,
        shuffles=1_000,
    )


def test_the_same_results_differ_by_nothing() -> None:
    picks = (ONLY_EXPECTED, WITH_UNRELATED)
    cards = [card(occupation, 1, picks[index % 2]) for index, occupation in enumerate(OCCUPATIONS)]

    comparison = compared(cards, cards)

    assert comparison.occupations == MIN_OCCUPATIONS
    assert comparison.repeats == (1,)
    assert comparison.changes.keys() == METRICS | {"overlap", "core_overlap"}
    measured = {key: change for key, change in comparison.changes.items() if key in METRICS}
    assert {
        (change.difference, change.interval, change.p_value) for change in measured.values()
    } == {(0.0, Interval(0.0, 0.0), 1.0)}
    assert comparison.changes["unrelated"] == Change(5 / 15, 5 / 15, Interval(0.0, 0.0), 1.0)
    assert not comparison.changes["unrelated"].clear


def test_a_drop_every_occupation_shares_is_clear() -> None:
    before = [
        card(
            occupation,
            1,
            (
                ("科目A", EXPECTED),
                *((f"科目{number}", UNRELATED) for number in range(index % 3 + 1)),
            ),
        )
        for index, occupation in enumerate(OCCUPATIONS)
    ]
    after = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]

    unrelated = compared(before, after).changes["unrelated"]

    assert unrelated.before == pytest.approx(19 / 29)
    assert unrelated.after == 0.0
    assert unrelated.interval is not None
    assert unrelated.interval.high < 0
    assert unrelated.p_value is not None
    assert unrelated.p_value < 0.01
    assert unrelated.clear


def test_a_change_in_one_occupation_alone_is_not_clear() -> None:
    before = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]
    after = [
        card(OCCUPATIONS[0], 1, (("科目A", EXPECTED), ("科目B", UNRELATED), ("科目C", UNRELATED))),
        *before[1:],
    ]

    comparison = compared(before, after)

    unrelated = comparison.changes["unrelated"]
    assert unrelated.difference == pytest.approx(2 / 12)
    assert unrelated.interval is not None
    assert unrelated.interval.low == 0.0
    assert unrelated.p_value == 1.0
    assert not unrelated.clear
    assert compared(before, after) == comparison


def test_a_drop_in_a_few_occupations_is_not_clear_even_when_the_interval_leaves_out_zero() -> None:
    dropped = OCCUPATIONS[:4]
    before = [
        card(occupation, 1, WITH_UNRELATED if occupation in dropped else ONLY_EXPECTED)
        for occupation in OCCUPATIONS
    ]
    after = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]

    unrelated = compared(before, after).changes["unrelated"]

    assert unrelated.difference == pytest.approx(-4 / 14)
    assert unrelated.interval is not None
    assert unrelated.interval.high < 0
    assert unrelated.p_value == pytest.approx(2 / 16, abs=0.03)
    assert not unrelated.clear


def test_the_values_average_the_repeats_like_the_summary() -> None:
    before = [
        *(card(occupation, 1, WITH_UNRELATED) for occupation in OCCUPATIONS),
        *(card(occupation, 2, ONLY_EXPECTED) for occupation in OCCUPATIONS),
    ]
    after = [
        card(occupation, repeat, ONLY_EXPECTED) for repeat in (1, 2) for occupation in OCCUPATIONS
    ]

    unrelated = compared(before, after).changes["unrelated"]

    assert unrelated.before == pytest.approx(0.25)
    assert unrelated.after == 0.0


def test_only_the_repeats_both_runs_scored_are_compared() -> None:
    before = [
        card(occupation, 1, WITH_UNRELATED if index < 5 else ONLY_EXPECTED)
        for index, occupation in enumerate(OCCUPATIONS)
    ] + [card(occupation, 2, WITH_UNRELATED) for occupation in OCCUPATIONS]
    after = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]

    comparison = compared(before, after)

    unrelated = comparison.changes["unrelated"]
    assert comparison.repeats == (1,)
    assert unrelated.before == pytest.approx(5 / 15)
    assert unrelated.after == 0.0
    assert unrelated.p_value == pytest.approx(2 / 32, abs=0.03)
    assert not unrelated.clear


def test_the_p_value_does_not_depend_on_how_many_times_the_interval_resamples() -> None:
    before = [
        card(occupation, 1, WITH_UNRELATED if index < 6 else ONLY_EXPECTED)
        for index, occupation in enumerate(OCCUPATIONS)
    ]
    after = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]
    runs = (scored_run(before, MIN_OCCUPATIONS), scored_run(after, MIN_OCCUPATIONS))

    few = compare_experiments(*runs, resamples=100, shuffles=1_000)
    many = compare_experiments(*runs, resamples=1_000, shuffles=1_000)

    assert few.changes["unrelated"].p_value == many.changes["unrelated"].p_value


def test_fewer_paired_occupations_than_were_checked_get_values_but_no_interval_or_test() -> None:
    cards = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS[:-1]]

    comparison = compared(cards, cards)

    assert comparison.occupations == MIN_OCCUPATIONS - 1
    assert comparison.changes["unrelated"] == Change(0.0, 0.0, None, None)
    assert all(change.interval is None for change in comparison.changes.values())
    assert all(change.p_value is None for change in comparison.changes.values())


def test_an_occupation_only_one_run_has_is_left_out_of_the_values() -> None:
    shared = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]
    extra = card("ほかの職業", 1, (("科目B", UNRELATED),))

    comparison = compared([*shared, extra], shared)

    assert comparison.occupations == MIN_OCCUPATIONS
    assert comparison.changes["unrelated"] == Change(0.0, 0.0, Interval(0.0, 0.0), 1.0)


def test_an_occupation_missing_from_a_scored_repeat_is_left_out_of_the_pairs() -> None:
    everyone = (*OCCUPATIONS, "職業10", "職業11")
    before = [
        *(card(occupation, 1, ONLY_EXPECTED) for occupation in everyone[:-1]),
        *(card(occupation, 2, ONLY_EXPECTED) for occupation in everyone[1:]),
    ]
    after = [
        card(occupation, repeat, WITH_UNRELATED)
        if occupation in (everyone[0], everyone[-1])
        else card(occupation, repeat, ONLY_EXPECTED)
        for repeat in (1, 2)
        for occupation in everyone
    ]

    comparison = compared(before, after)

    assert comparison.repeats == (1, 2)
    assert comparison.occupations == len(everyone) - 2
    assert comparison.changes["unrelated"] == Change(0.0, 0.0, Interval(0.0, 0.0), 1.0)


def test_the_overlap_between_repeats_is_compared_by_occupation() -> None:
    before = [
        card(occupation, repeat, ((name, EXPECTED),))
        for repeat, name in ((1, "科目A"), (2, "科目B"))
        for occupation in OCCUPATIONS
    ]
    after = [
        card(occupation, repeat, ONLY_EXPECTED) for repeat in (1, 2) for occupation in OCCUPATIONS
    ]

    changes = compared(before, after).changes

    assert changes["overlap"].interval == Interval(1.0, 1.0)
    assert changes["core_overlap"].interval == Interval(1.0, 1.0)
    assert changes["overlap"].p_value == pytest.approx(2 / 1024, abs=0.005)
    assert changes["overlap"].clear


def test_a_share_left_undefined_in_either_run_has_no_difference() -> None:
    nothing = [card(occupation, 1, ()) for occupation in OCCUPATIONS]
    something = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]

    changes = compared(nothing, something).changes

    assert changes["unrelated"] == Change(None, 0.0, None, None)
    assert changes["unrelated"].difference is None
    assert changes["cores"].interval == Interval(1.0, 1.0)


def test_a_share_some_resamples_cannot_define_gets_no_interval() -> None:
    before = [
        card(OCCUPATIONS[0], 1, ONLY_EXPECTED),
        *(card(occupation, 1, ()) for occupation in OCCUPATIONS[1:]),
    ]
    after = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]

    changes = compared(before, after).changes

    assert changes["core_precision"] == Change(1.0, 1.0, None, 1.0)
    assert changes["cores"].interval is not None


@pytest.mark.parametrize(
    ("p_value", "clear"),
    [(0.049, True), (0.05, False), (0.5, False), (None, False)],
    ids=["below", "at", "above", "untested"],
)
def test_a_change_is_clear_only_when_its_p_value_is_below_five_percent(
    p_value: float | None, clear: bool
) -> None:
    assert Change(0.2, 0.1, Interval(-0.15, -0.05), p_value).clear is clear
