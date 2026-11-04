from collections.abc import Mapping

import pytest

from app.application.measure_reason_agreement import MeasureReasonAgreement
from app.application.ports import ReasonJudgeError, ReasonJudgeUnavailableError
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


class FixedJudge:
    def __init__(self, grades: Mapping[str, ReasonGrade]) -> None:
        self._grades = grades
        self.asked: list[ReasonCase] = []

    def judge(self, case: ReasonCase) -> ReasonVote:
        self.asked.append(case)
        return ReasonVote(self._grades[case.reason], "判定器の根拠")


def answered(key: str, relevance: Relevance, answer: ReasonGrade) -> JudgedReason:
    case = ReasonCase(
        "職業",
        "解釈",
        None,
        relevance,
        f"授業{key}",
        "柱" if relevance is Relevance.FOUNDATION else None,
        f"理由{key}",
    )
    votes = tuple(ReasonVote(answer, "根拠") for _ in range(3))
    return JudgedReason(SampledReason(key, Split.TUNE, case), votes)


REASONS = [
    answered("1", Relevance.CORE, SPECIFIC),
    answered("2", Relevance.CORE, VAGUE),
    answered("3", Relevance.CORE, ABSENT),
    answered("4", Relevance.FOUNDATION, SPECIFIC),
    answered("5", Relevance.FOUNDATION, VAGUE),
]


def test_every_reason_is_judged_once_in_order() -> None:
    judge = FixedJudge({f"理由{key}": VAGUE for key in "12345"})

    agreement = MeasureReasonAgreement(judge).run(REASONS)

    assert [case.reason for case in judge.asked] == [f"理由{key}" for key in "12345"]
    assert [pair.reason for pair in agreement.pairs] == REASONS


def test_a_judge_that_matches_every_answer_is_adoptable() -> None:
    judge = FixedJudge({reason.sample.case.reason: reason.answer for reason in REASONS})

    agreement = MeasureReasonAgreement(judge).run(REASONS)

    assert agreement.kappa == pytest.approx(1.0)
    assert agreement.adoptable
    assert all(pair.agrees for pair in agreement.pairs)


def test_the_agreement_is_split_by_pillar_and_foundation_and_counted_by_grade_pair() -> None:
    grades = {"理由1": SPECIFIC, "理由2": SPECIFIC, "理由3": ABSENT, "理由4": VAGUE, "理由5": VAGUE}

    agreement = MeasureReasonAgreement(FixedJudge(grades)).run(REASONS)

    assert [pair.reason.sample.key for pair in agreement.of(Relevance.CORE).pairs] == [
        "1",
        "2",
        "3",
    ]
    assert agreement.of(Relevance.FOUNDATION).kappa == pytest.approx(0.0)
    assert agreement.confusion == {
        (SPECIFIC, SPECIFIC): 1,
        (VAGUE, SPECIFIC): 1,
        (ABSENT, ABSENT): 1,
        (SPECIFIC, VAGUE): 1,
        (VAGUE, VAGUE): 1,
    }


def test_a_judge_below_the_kappa_to_adopt_is_not_adoptable() -> None:
    agreement = MeasureReasonAgreement(FixedJudge({f"理由{key}": VAGUE for key in "12345"})).run(
        REASONS
    )

    assert agreement.kappa == pytest.approx(0.0)
    assert not agreement.adoptable


class PartlyFailingJudge(FixedJudge):
    def judge(self, case: ReasonCase) -> ReasonVote:
        if case.reason == "理由2":
            raise ReasonJudgeError("答えられません")
        return super().judge(case)


def test_a_reason_the_judge_cannot_answer_is_kept_as_a_failure_and_blocks_adoption() -> None:
    judge = PartlyFailingJudge({reason.sample.case.reason: reason.answer for reason in REASONS})

    agreement = MeasureReasonAgreement(judge).run(REASONS)

    assert [failure.reason.sample.key for failure in agreement.failures] == ["2"]
    assert agreement.failures[0].message == "答えられません"
    assert len(agreement.pairs) == 4
    assert agreement.kappa == pytest.approx(1.0)
    assert not agreement.adoptable
    assert len(agreement.of(Relevance.CORE).failures) == 1
    assert not agreement.of(Relevance.FOUNDATION).failures


def test_a_kind_without_judged_reasons_has_no_kappa() -> None:
    judge = PartlyFailingJudge({reason.sample.case.reason: reason.answer for reason in REASONS})

    only_failed = MeasureReasonAgreement(judge).run([REASONS[1]])

    assert only_failed.of(Relevance.CORE).kappa is None
    assert only_failed.of(Relevance.FOUNDATION).kappa is None


class UnreachableJudge(FixedJudge):
    def judge(self, case: ReasonCase) -> ReasonVote:
        raise ReasonJudgeUnavailableError("呼べません")


def test_a_judge_that_cannot_be_called_stops_the_measurement() -> None:
    with pytest.raises(ReasonJudgeUnavailableError, match="呼べません"):
        MeasureReasonAgreement(UnreachableJudge({})).run(REASONS)


def test_the_agreed_count_is_the_number_of_matching_pairs() -> None:
    grades = {"理由1": SPECIFIC, "理由2": SPECIFIC, "理由3": ABSENT, "理由4": VAGUE, "理由5": VAGUE}

    assert MeasureReasonAgreement(FixedJudge(grades)).run(REASONS).agreed == 3


class AlwaysFailingJudge(FixedJudge):
    def judge(self, case: ReasonCase) -> ReasonVote:
        self.asked.append(case)
        raise ReasonJudgeError("使えない答え")


def test_answers_that_cannot_be_used_three_times_in_a_row_stop_the_measurement() -> None:
    judge = AlwaysFailingJudge({})

    with pytest.raises(ReasonJudgeUnavailableError, match="続けて 3 件の答えを使えなかった"):
        MeasureReasonAgreement(judge).run(REASONS)
    assert len(judge.asked) == 3
