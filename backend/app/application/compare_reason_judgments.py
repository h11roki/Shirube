from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from random import Random

from app.application.compare_experiments import (
    MIN_OCCUPATIONS,
    RESAMPLES,
    Interval,
    interval_of,
)
from app.application.reason_judging import GRADES, SEED, JudgedReason, ReasonGrade

Tallies = Mapping[str, Counter[ReasonGrade]]


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


def _tallies(reasons: Sequence[JudgedReason]) -> Tallies:
    tallies: defaultdict[str, Counter[ReasonGrade]] = defaultdict(Counter)
    for reason in reasons:
        tallies[reason.sample.case.occupation][reason.answer] += 1
    return tallies


def _share(tallies: Tallies, grade: ReasonGrade, weights: Counter[str]) -> float | None:
    total = sum(
        weight * tallies[name].total() for name, weight in weights.items() if name in tallies
    )
    if total == 0:
        return None
    graded = sum(
        weight * tallies[name][grade] for name, weight in weights.items() if name in tallies
    )
    return graded / total


def share_changes(
    before: Sequence[JudgedReason],
    after: Sequence[JudgedReason],
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> dict[ReasonGrade, ShareChange]:
    old, new = _tallies(before), _tallies(after)
    occupations = sorted(old.keys() | new.keys())
    everyone = Counter(occupations)
    picker = Random(seed)
    samples = (
        [Counter(picker.choices(occupations, k=len(occupations))) for _ in range(resamples)]
        if len(occupations) >= MIN_OCCUPATIONS
        else []
    )
    changes = {}
    for grade in GRADES:
        before_share, after_share = _share(old, grade, everyone), _share(new, grade, everyone)
        if before_share is None or after_share is None:
            changes[grade] = ShareChange(before_share, after_share, None)
            continue
        differences: list[float] = []
        for chosen in samples:
            resampled_old, resampled_new = _share(old, grade, chosen), _share(new, grade, chosen)
            if resampled_old is None or resampled_new is None:
                differences = []
                break
            differences.append(resampled_new - resampled_old)
        changes[grade] = ShareChange(before_share, after_share, interval_of(differences))
    return changes
