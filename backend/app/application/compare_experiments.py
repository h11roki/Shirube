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

Statistic = Callable[[Sequence[str]], float | None]


@dataclass(frozen=True)
class Difference:
    estimate: float
    low: float
    high: float

    @property
    def clear(self) -> bool:
        return self.low > 0 or self.high < 0


@dataclass(frozen=True)
class Comparison:
    occupations: int
    differences: dict[str, Difference]


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


def _difference(
    old: Statistic, new: Statistic, occupations: Sequence[str], samples: Sequence[Sequence[str]]
) -> Difference | None:
    before, after = old(occupations), new(occupations)
    if before is None or after is None:
        return None
    resampled = []
    for chosen in samples:
        chosen_before, chosen_after = old(chosen), new(chosen)
        if chosen_before is not None and chosen_after is not None:
            resampled.append(chosen_after - chosen_before)
    if not resampled:
        return None
    resampled.sort()
    tail = (1 - CONFIDENCE) / 2
    return Difference(
        after - before,
        resampled[int(tail * len(resampled))],
        resampled[math.ceil((1 - tail) * len(resampled)) - 1],
    )


def compare_experiments(
    before: ScoredRun, after: ScoredRun, resamples: int = RESAMPLES, seed: int = SEED
) -> Comparison:
    occupations = sorted(before.occupations & after.occupations)
    if len(occupations) < MIN_OCCUPATIONS:
        return Comparison(len(occupations), {})
    generator = Random(seed)
    samples = [generator.choices(occupations, k=len(occupations)) for _ in range(resamples)]
    old, new = _statistics(before), _statistics(after)
    differences = {
        key: difference
        for key in sorted(old.keys() & new.keys())
        if (difference := _difference(old[key], new[key], occupations, samples)) is not None
    }
    return Comparison(len(occupations), differences)
