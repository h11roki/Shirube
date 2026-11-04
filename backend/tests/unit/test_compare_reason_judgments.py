import pytest

from app.application.compare_reason_judgments import compare_shares
from app.application.reason_judging import (
    JudgedReason,
    ReasonCase,
    ReasonGrade,
    ReasonJudgingError,
    ReasonVote,
    SampledReason,
    Split,
)
from app.domain.recommendation import Relevance

SPECIFIC, VAGUE, ABSENT = ReasonGrade.SPECIFIC, ReasonGrade.VAGUE, ReasonGrade.ABSENT
CORE, FOUNDATION = Relevance.CORE, Relevance.FOUNDATION
MANY = [f"職業{index}" for index in range(12)]


def judged(
    occupation: str, number: int, answer: ReasonGrade, relevance: Relevance = CORE
) -> JudgedReason:
    pillar = "柱" if relevance is FOUNDATION else None
    case = ReasonCase(occupation, "解釈", None, relevance, f"授業{number}", pillar, "理由")
    votes = tuple(ReasonVote(answer, "根拠") for _ in range(3))
    key = f"{occupation}-{relevance.value}-{number}"
    return JudgedReason(SampledReason(key, Split.TUNE, case), votes)


def side(
    answers_by_occupation: dict[str, list[ReasonGrade]], relevance: Relevance = CORE
) -> list[JudgedReason]:
    return [
        judged(occupation, number, answer, relevance)
        for occupation, answers in answers_by_occupation.items()
        for number, answer in enumerate(answers)
    ]


def test_the_shares_and_their_differences_come_from_all_reasons_of_each_kind() -> None:
    before = side({"甲": [SPECIFIC, VAGUE], "乙": [VAGUE, ABSENT]})
    after = side({"甲": [SPECIFIC, SPECIFIC], "乙": [SPECIFIC, VAGUE]})
    foundations = side({"甲": [ABSENT]}, FOUNDATION)

    comparison = compare_shares(before + foundations, after, ["甲", "乙"], resamples=200)

    cores = comparison.changes[CORE]
    assert cores[SPECIFIC].before == pytest.approx(0.25)
    assert cores[SPECIFIC].after == pytest.approx(0.75)
    assert cores[SPECIFIC].difference == pytest.approx(0.5)
    assert cores[ABSENT].difference == pytest.approx(-0.25)
    assert comparison.changes[FOUNDATION][ABSENT].before == pytest.approx(1.0)
    assert comparison.changes[FOUNDATION][ABSENT].after is None
    assert comparison.occupations == 2
    assert not comparison.enough


def test_a_difference_present_in_every_occupation_has_an_interval_away_from_zero() -> None:
    before = side({name: [VAGUE] * 3 for name in MANY})
    after = side({name: [SPECIFIC] * 3 for name in MANY})

    comparison = compare_shares(before, after, MANY, resamples=200)

    change = comparison.changes[CORE][SPECIFIC]
    assert comparison.enough
    assert change.interval is not None
    assert change.interval.low == pytest.approx(1.0)
    assert change.clear


def test_identical_sides_have_an_interval_around_zero_and_no_clear_change() -> None:
    reasons = side(
        {name: [SPECIFIC, VAGUE] if index % 2 else [VAGUE] for index, name in enumerate(MANY)}
    )

    change = compare_shares(reasons, reasons, MANY, resamples=200).changes[CORE][SPECIFIC]

    assert change.interval is not None
    assert change.interval.low <= 0 <= change.interval.high
    assert not change.clear


def test_fewer_occupations_than_the_minimum_give_no_interval() -> None:
    before = side({name: [VAGUE] * 3 for name in MANY[:9]})
    after = side({name: [SPECIFIC] * 3 for name in MANY[:9]})

    comparison = compare_shares(before, after, MANY[:9], resamples=200)

    change = comparison.changes[CORE][SPECIFIC]
    assert not comparison.enough
    assert change.difference == pytest.approx(1.0)
    assert change.interval is None
    assert not change.clear


def test_the_same_seed_gives_the_same_intervals() -> None:
    before = side(
        {name: [SPECIFIC, VAGUE] if index % 2 else [VAGUE] for index, name in enumerate(MANY)}
    )
    after = side(
        {
            name: [SPECIFIC, SPECIFIC] if index % 3 else [SPECIFIC, VAGUE]
            for index, name in enumerate(MANY)
        }
    )

    assert compare_shares(before, after, MANY, resamples=300) == compare_shares(
        before, after, MANY, resamples=300
    )
    assert compare_shares(before, after, MANY, resamples=300, seed=1) != compare_shares(
        before, after, MANY, resamples=300
    )


def test_a_side_without_reasons_has_no_share_and_no_interval() -> None:
    comparison = compare_shares([], side({"甲": [SPECIFIC]}), ["甲"], resamples=10)

    change = comparison.changes[CORE][SPECIFIC]
    assert change.before is None
    assert change.after == pytest.approx(1.0)
    assert change.interval is None
    assert change.difference is None


def test_a_reason_of_an_occupation_outside_the_shared_ones_is_refused() -> None:
    with pytest.raises(ReasonJudgingError, match="選び直す職業に無い職業の理由があります: 乙"):
        compare_shares(side({"甲": [VAGUE]}), side({"乙": [SPECIFIC]}), ["甲"], resamples=10)


def test_occupations_without_sampled_reasons_still_take_part_in_the_resampling() -> None:
    before = side({name: [VAGUE] * 2 for name in MANY[:6]})
    after = side({name: [SPECIFIC] * 2 for name in MANY[6:]})

    change = compare_shares(before, after, MANY, resamples=200).changes[CORE][SPECIFIC]

    assert change.difference == pytest.approx(1.0)
    assert change.interval is not None
