from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from random import Random

from app.application.compare_experiments import CONFIDENCE, RESAMPLES, Interval
from app.application.reason_judging import SEED, JudgedReason, ReasonGrade


@dataclass(frozen=True)
class ShareChange:
    before: float | None
    after: float | None
    interval: Interval | None

    @property
    def difference(self) -> float | None:
        if self.before is None or self.after is None:
            return None
        return self.after - self.before

    @property
    def clear(self) -> bool:
        return self.interval is not None and (self.interval.low > 0 or self.interval.high < 0)


def _share(
    reasons: Sequence[JudgedReason], grade: ReasonGrade, weights: Counter[str]
) -> float | None:
    total = sum(weights[reason.sample.case.occupation] for reason in reasons)
    if total == 0:
        return None
    graded = sum(
        weights[reason.sample.case.occupation] for reason in reasons if reason.answer is grade
    )
    return graded / total


def share_change(
    before: Sequence[JudgedReason],
    after: Sequence[JudgedReason],
    grade: ReasonGrade,
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> ShareChange:
    occupations = sorted({reason.sample.case.occupation for reason in (*before, *after)})
    everyone = Counter(occupations)
    old, new = _share(before, grade, everyone), _share(after, grade, everyone)
    if old is None or new is None:
        return ShareChange(old, new, None)
    picker = Random(seed)
    differences = []
    for _ in range(resamples):
        chosen = Counter(picker.choices(occupations, k=len(occupations)))
        resampled_old, resampled_new = _share(before, grade, chosen), _share(after, grade, chosen)
        if resampled_old is None or resampled_new is None:
            return ShareChange(old, new, None)
        differences.append(resampled_new - resampled_old)
    differences.sort()
    cut = round(len(differences) * (1 - CONFIDENCE) / 2)
    return ShareChange(
        old, new, Interval(differences[cut], differences[len(differences) - 1 - cut])
    )
