import pytest

from app.application.compare_reason_judgments import share_change
from app.application.reason_judging import (
    JudgedReason,
    ReasonCase,
    ReasonGrade,
    ReasonVote,
    SampledReason,
    Split,
)
from app.domain.recommendation import Relevance

SPECIFIC, VAGUE = ReasonGrade.SPECIFIC, ReasonGrade.VAGUE


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


def test_the_shares_and_their_difference_come_from_all_reasons_of_each_side() -> None:
    before = side({"甲": [SPECIFIC, VAGUE], "乙": [VAGUE, VAGUE]})
    after = side({"甲": [SPECIFIC, SPECIFIC], "乙": [SPECIFIC, VAGUE]})

    change = share_change(before, after, SPECIFIC, resamples=200)

    assert change.before == pytest.approx(0.25)
    assert change.after == pytest.approx(0.75)
    assert change.difference == pytest.approx(0.5)


def test_a_difference_present_in_every_occupation_has_an_interval_away_from_zero() -> None:
    before = side({name: [VAGUE] * 3 for name in "甲乙丙丁戊"})
    after = side({name: [SPECIFIC] * 3 for name in "甲乙丙丁戊"})

    change = share_change(before, after, SPECIFIC, resamples=200)

    assert change.interval is not None
    assert change.interval.low == pytest.approx(1.0)
    assert change.clear


def test_identical_sides_have_an_interval_around_zero_and_no_clear_change() -> None:
    reasons = side({"甲": [SPECIFIC, VAGUE], "乙": [VAGUE, SPECIFIC], "丙": [SPECIFIC, VAGUE]})

    change = share_change(reasons, reasons, SPECIFIC, resamples=200)

    assert change.interval is not None
    assert change.interval.low <= 0 <= change.interval.high
    assert not change.clear


def test_the_same_seed_gives_the_same_interval() -> None:
    before = side({"甲": [SPECIFIC, VAGUE], "乙": [VAGUE, VAGUE], "丙": [SPECIFIC]})
    after = side({"甲": [SPECIFIC], "乙": [SPECIFIC, VAGUE], "丙": [SPECIFIC, SPECIFIC]})

    assert share_change(before, after, SPECIFIC, resamples=300) == share_change(
        before, after, SPECIFIC, resamples=300
    )
    assert share_change(before, after, SPECIFIC, resamples=300, seed=1) != share_change(
        before, after, SPECIFIC, resamples=300
    )


def test_a_side_without_reasons_has_no_share_and_no_interval() -> None:
    change = share_change([], side({"甲": [SPECIFIC]}), SPECIFIC, resamples=10)

    assert change.before is None
    assert change.after == pytest.approx(1.0)
    assert change.interval is None
    assert change.difference is None
