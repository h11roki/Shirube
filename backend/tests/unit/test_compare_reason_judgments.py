import pytest

from app.application.compare_reason_judgments import share_changes
from app.application.reason_judging import (
    JudgedReason,
    ReasonCase,
    ReasonGrade,
    ReasonVote,
    SampledReason,
    Split,
)
from app.domain.recommendation import Relevance

SPECIFIC, VAGUE, ABSENT = ReasonGrade.SPECIFIC, ReasonGrade.VAGUE, ReasonGrade.ABSENT
MANY = [f"職業{index}" for index in range(12)]


def judged(occupation: str, number: int, answer: ReasonGrade) -> JudgedReason:
    case = ReasonCase(occupation, "解釈", None, Relevance.CORE, f"授業{number}", None, "理由")
    votes = tuple(ReasonVote(answer, "根拠") for _ in range(3))
    return JudgedReason(SampledReason(f"{occupation}-{number}", Split.TUNE, case), votes)


def side(answers_by_occupation: dict[str, list[ReasonGrade]]) -> list[JudgedReason]:
    return [
        judged(occupation, number, answer)
        for occupation, answers in answers_by_occupation.items()
        for number, answer in enumerate(answers)
    ]


def test_the_shares_and_their_differences_come_from_all_reasons_of_each_side() -> None:
    before = side({"甲": [SPECIFIC, VAGUE], "乙": [VAGUE, ABSENT]})
    after = side({"甲": [SPECIFIC, SPECIFIC], "乙": [SPECIFIC, VAGUE]})

    changes = share_changes(before, after, resamples=200)

    assert changes[SPECIFIC].before == pytest.approx(0.25)
    assert changes[SPECIFIC].after == pytest.approx(0.75)
    assert changes[SPECIFIC].difference == pytest.approx(0.5)
    assert changes[ABSENT].difference == pytest.approx(-0.25)
    assert set(changes) == set(ReasonGrade)


def test_a_difference_present_in_every_occupation_has_an_interval_away_from_zero() -> None:
    before = side({name: [VAGUE] * 3 for name in MANY})
    after = side({name: [SPECIFIC] * 3 for name in MANY})

    change = share_changes(before, after, resamples=200)[SPECIFIC]

    assert change.interval is not None
    assert change.interval.low == pytest.approx(1.0)
    assert change.clear


def test_identical_sides_have_an_interval_around_zero_and_no_clear_change() -> None:
    reasons = side(
        {name: [SPECIFIC, VAGUE] if index % 2 else [VAGUE] for index, name in enumerate(MANY)}
    )

    change = share_changes(reasons, reasons, resamples=200)[SPECIFIC]

    assert change.interval is not None
    assert change.interval.low <= 0 <= change.interval.high
    assert not change.clear


def test_fewer_occupations_than_the_minimum_give_no_interval() -> None:
    before = side({name: [VAGUE] * 3 for name in MANY[:9]})
    after = side({name: [SPECIFIC] * 3 for name in MANY[:9]})

    change = share_changes(before, after, resamples=200)[SPECIFIC]

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

    assert share_changes(before, after, resamples=300) == share_changes(
        before, after, resamples=300
    )
    assert share_changes(before, after, resamples=300, seed=1) != share_changes(
        before, after, resamples=300
    )


def test_a_side_without_reasons_has_no_share_and_no_interval() -> None:
    change = share_changes([], side({"甲": [SPECIFIC]}), resamples=10)[SPECIFIC]

    assert change.before is None
    assert change.after == pytest.approx(1.0)
    assert change.interval is None
    assert change.difference is None
