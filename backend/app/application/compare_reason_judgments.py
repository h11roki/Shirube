from collections import Counter, defaultdict
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from random import Random

from app.application.compare_experiments import (
    MIN_OCCUPATIONS,
    RESAMPLES,
    Change,
    interval_of,
)
from app.application.reason_judging import (
    GRADES,
    SEED,
    JudgedReason,
    ReasonGrade,
    ReasonJudgingError,
)
from app.domain.recommendation import Relevance

Tallies = Mapping[str, Counter[ReasonGrade]]


@dataclass(frozen=True)
class ShareChange(Change):
    @property
    def clear(self) -> bool:
        return self.interval is not None and (self.interval.low > 0 or self.interval.high < 0)


@dataclass(frozen=True)
class ShareComparison:
    occupations: int
    changes: Mapping[Relevance, Mapping[ReasonGrade, ShareChange]]

    @property
    def enough(self) -> bool:
        return self.occupations >= MIN_OCCUPATIONS


def _tallies(reasons: Iterable[JudgedReason]) -> Tallies:
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


def _change(
    old: Tallies,
    new: Tallies,
    grade: ReasonGrade,
    everyone: Counter[str],
    samples: list[Counter[str]],
) -> ShareChange:
    before, after = _share(old, grade, everyone), _share(new, grade, everyone)
    if before is None or after is None:
        return ShareChange(before, after, None, None)
    differences: list[float] = []
    for chosen in samples:
        resampled_old, resampled_new = _share(old, grade, chosen), _share(new, grade, chosen)
        if resampled_old is None or resampled_new is None:
            differences = []
            break
        differences.append(resampled_new - resampled_old)
    return ShareChange(before, after, interval_of(differences), None)


def compare_shares(
    before: Collection[JudgedReason],
    after: Collection[JudgedReason],
    occupations: Collection[str],
    resamples: int = RESAMPLES,
    seed: int = SEED,
) -> ShareComparison:
    names = sorted(occupations)
    outside = sorted({reason.sample.case.occupation for reason in (*before, *after)} - set(names))
    if outside:
        raise ReasonJudgingError(f"選び直す職業に無い職業の理由があります: {'、'.join(outside)}")
    everyone = Counter(names)
    picker = Random(seed)
    samples = (
        [Counter(picker.choices(names, k=len(names))) for _ in range(resamples)]
        if len(names) >= MIN_OCCUPATIONS
        else []
    )
    changes = {}
    for relevance in Relevance:
        old = _tallies(reason for reason in before if reason.sample.case.relevance is relevance)
        new = _tallies(reason for reason in after if reason.sample.case.relevance is relevance)
        changes[relevance] = {
            grade: _change(old, new, grade, everyone, samples) for grade in GRADES
        }
    return ShareComparison(len(names), changes)
