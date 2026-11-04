from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from app.application.ports import ReasonJudge, ReasonJudgeError, ReasonJudgeUnavailableError
from app.application.reason_judging import JudgedReason, ReasonGrade, ReasonVote, cohen_kappa
from app.domain.recommendation import Relevance

KAPPA_TO_ADOPT = 0.6
FAILURE_STREAK_LIMIT = 3


@dataclass(frozen=True)
class JudgedPair:
    reason: JudgedReason
    vote: ReasonVote

    @property
    def agrees(self) -> bool:
        return self.vote.grade is self.reason.answer


@dataclass(frozen=True)
class FailedJudgment:
    reason: JudgedReason
    message: str


@dataclass(frozen=True)
class ReasonAgreement:
    pairs: tuple[JudgedPair, ...]
    failures: tuple[FailedJudgment, ...] = ()

    def of(self, relevance: Relevance) -> "ReasonAgreement":
        return ReasonAgreement(
            tuple(pair for pair in self.pairs if pair.reason.sample.case.relevance is relevance),
            tuple(
                failure
                for failure in self.failures
                if failure.reason.sample.case.relevance is relevance
            ),
        )

    @property
    def agreed(self) -> int:
        return sum(1 for pair in self.pairs if pair.agrees)

    @property
    def kappa(self) -> float | None:
        if not self.pairs:
            return None
        return cohen_kappa([(pair.reason.answer, pair.vote.grade) for pair in self.pairs])

    @property
    def adoptable(self) -> bool:
        kappa = self.kappa
        return not self.failures and kappa is not None and kappa >= KAPPA_TO_ADOPT

    @property
    def confusion(self) -> Counter[tuple[ReasonGrade, ReasonGrade]]:
        return Counter((pair.reason.answer, pair.vote.grade) for pair in self.pairs)


class MeasureReasonAgreement:
    def __init__(self, judge: ReasonJudge) -> None:
        self._judge = judge

    def run(self, reasons: Sequence[JudgedReason]) -> ReasonAgreement:
        pairs: list[JudgedPair] = []
        failures: list[FailedJudgment] = []
        streak = 0
        for reason in reasons:
            try:
                pairs.append(JudgedPair(reason, self._judge.judge(reason.sample.case)))
                streak = 0
            except ReasonJudgeError as error:
                failures.append(FailedJudgment(reason, str(error)))
                streak += 1
                if streak == FAILURE_STREAK_LIMIT:
                    raise ReasonJudgeUnavailableError(
                        f"続けて {streak} 件の答えを使えなかったので止めました。最後は {error}"
                    ) from error
        return ReasonAgreement(tuple(pairs), tuple(failures))
