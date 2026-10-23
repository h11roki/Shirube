from collections.abc import Sequence

import pytest

from app.application.compare_experiments import (
    MIN_OCCUPATIONS,
    Comparison,
    Difference,
    compare_experiments,
)
from app.application.evaluate_selection import ExpectedCourse, Judgment, Pick, SelectionResult
from app.application.run_experiment import Scorecard, scored_run
from app.domain.recommendation import Relevance

OCCUPATIONS = tuple(f"職業{index}" for index in range(MIN_OCCUPATIONS))
EXPECTED, UNRELATED = Judgment.EXPECTED, Judgment.UNRELATED
ONLY_EXPECTED = (("科目A", EXPECTED),)
NO_CHANGE = Difference(0.0, 0.0, 0.0)


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
    )


def test_the_same_results_differ_by_nothing() -> None:
    picks = (ONLY_EXPECTED, (("科目A", EXPECTED), ("科目B", UNRELATED)))
    cards = [card(occupation, 1, picks[index % 2]) for index, occupation in enumerate(OCCUPATIONS)]

    comparison = compared(cards, cards)

    assert comparison.occupations == MIN_OCCUPATIONS
    assert comparison.differences.keys() == {
        "recall@10",
        "recall@20",
        "candidate_recall",
        "core_precision",
        "expected_as_core",
        "unrelated",
        "cores",
        "foundations",
    }
    assert set(comparison.differences.values()) == {NO_CHANGE}


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

    unrelated = compared(before, after).differences["unrelated"]

    assert unrelated.estimate == pytest.approx(-19 / 29)
    assert unrelated.high < 0
    assert unrelated.clear


def test_a_change_in_one_occupation_alone_is_not_clear() -> None:
    before = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]
    after = [
        card(OCCUPATIONS[0], 1, (("科目A", EXPECTED), ("科目B", UNRELATED), ("科目C", UNRELATED))),
        *before[1:],
    ]

    comparison = compared(before, after)

    unrelated = comparison.differences["unrelated"]
    assert unrelated.estimate == pytest.approx(2 / 12)
    assert unrelated.low == 0.0
    assert not unrelated.clear
    assert compared(before, after) == comparison


def test_the_estimate_averages_the_repeats_like_the_summary() -> None:
    before = [
        *(
            card(occupation, 1, (("科目A", EXPECTED), ("科目B", UNRELATED)))
            for occupation in OCCUPATIONS
        ),
        *(card(occupation, 2, ONLY_EXPECTED) for occupation in OCCUPATIONS),
    ]
    after = [
        card(occupation, repeat, ONLY_EXPECTED) for repeat in (1, 2) for occupation in OCCUPATIONS
    ]

    unrelated = compared(before, after).differences["unrelated"]

    assert unrelated.estimate == pytest.approx(-0.25)


def test_fewer_paired_occupations_than_were_checked_get_no_interval() -> None:
    cards = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS[:-1]]

    assert compared(cards, cards) == Comparison(MIN_OCCUPATIONS - 1, {})


def test_an_occupation_only_one_run_has_is_left_out_of_the_pairs() -> None:
    shared = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]
    extra = card("ほかの職業", 1, (("科目B", UNRELATED),))

    comparison = compared([*shared, extra], shared)

    assert comparison.occupations == MIN_OCCUPATIONS
    assert comparison.differences["unrelated"] == NO_CHANGE


def test_the_overlap_between_repeats_is_compared_by_occupation() -> None:
    before = [
        card(occupation, repeat, ((name, EXPECTED),))
        for repeat, name in ((1, "科目A"), (2, "科目B"))
        for occupation in OCCUPATIONS
    ]
    after = [
        card(occupation, repeat, ONLY_EXPECTED) for repeat in (1, 2) for occupation in OCCUPATIONS
    ]

    differences = compared(before, after).differences

    assert differences["overlap"] == Difference(1.0, 1.0, 1.0)
    assert differences["core_overlap"] == Difference(1.0, 1.0, 1.0)


def test_a_share_left_undefined_in_either_run_has_no_difference() -> None:
    nothing = [card(occupation, 1, ()) for occupation in OCCUPATIONS]
    something = [card(occupation, 1, ONLY_EXPECTED) for occupation in OCCUPATIONS]

    differences = compared(nothing, something).differences

    assert {"core_precision", "unrelated"}.isdisjoint(differences)
    assert differences["cores"] == Difference(1.0, 1.0, 1.0)
