import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from random import Random

from app.application.run_experiment import (
    Ratio,
    ScoredRun,
    mean_of_defined,
    overlaps,
    picked,
    picked_cores,
    pooled,
    ratios,
)

RESAMPLES = 10_000
SEED = 0
CONFIDENCE = 0.95
MIN_OCCUPATIONS = 10
TOLERANCE = 1e-9

Statistic = Callable[[Sequence[str]], float | None]


@dataclass(frozen=True)
class Interval:
    low: float
    high: float

    @property
    def clear(self) -> bool:
        return self.low > TOLERANCE or self.high < -TOLERANCE


@dataclass(frozen=True)
class Change:
    before: float | None
    after: float | None
    interval: Interval | None

    @property
    def difference(self) -> float | None:
        if self.before is None or self.after is None:
            return None
        return self.after - self.before


@dataclass(frozen=True)
class Comparison:
    occupations: int
    changes: dict[str, Change]


def _pooled_mean(
    key: str, repeats: Sequence[Mapping[str, Mapping[str, Ratio]]], chosen: Sequence[str]
) -> float | None:
    return mean_of_defined(
        pooled([cells[occupation][key] for occupation in chosen if occupation in cells])
        for cells in repeats
    )


def _overlap_mean(values: Mapping[str, float], chosen: Sequence[str]) -> float | None:
    return mean_of_defined(values.get(occupation) for occupation in chosen)


def _statistics(run: ScoredRun) -> dict[str, Statistic]:
    per_repeat = [{card.occupation: ratios(card) for card in group} for group in run.repeats]
    keys = {key for cells in per_repeat for entry in cells.values() for key in entry}
    return {
        **{key: partial(_pooled_mean, key, per_repeat) for key in keys},
        "overlap": partial(_overlap_mean, overlaps(run.cards, picked)),
        "core_overlap": partial(_overlap_mean, overlaps(run.cards, picked_cores)),
    }


def _interval(old: Statistic, new: Statistic, samples: Sequence[Sequence[str]]) -> Interval | None:
    differences = []
    for chosen in samples:
        before, after = old(chosen), new(chosen)
        if before is None or after is None:
            return None
        differences.append(after - before)
    if not differences:
        return None
    differences.sort()
    tail = (1 - CONFIDENCE) / 2
    return Interval(
        differences[int(tail * len(differences))],
        differences[math.ceil((1 - tail) * len(differences)) - 1],
    )


def _change(
    old: Statistic, new: Statistic, occupations: Sequence[str], samples: Sequence[Sequence[str]]
) -> Change:
    before, after = old(occupations), new(occupations)
    if before is None or after is None:
        return Change(before, after, None)
    return Change(before, after, _interval(old, new, samples))


def compare_experiments(
    before: ScoredRun, after: ScoredRun, resamples: int = RESAMPLES, seed: int = SEED
) -> Comparison:
    occupations = sorted(before.occupations & after.occupations)
    generator = Random(seed)
    samples = (
        [generator.choices(occupations, k=len(occupations)) for _ in range(resamples)]
        if len(occupations) >= MIN_OCCUPATIONS
        else []
    )
    old, new = _statistics(before), _statistics(after)
    return Comparison(
        len(occupations),
        {
            key: _change(old[key], new[key], occupations, samples)
            for key in sorted(old.keys() & new.keys())
        },
    )
