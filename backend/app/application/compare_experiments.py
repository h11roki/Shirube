from collections.abc import Callable, Sequence
from dataclasses import dataclass
from random import Random

from app.application.run_experiment import (
    METRICS,
    Ratio,
    Scorecard,
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
OVERLAPS: dict[str, Callable[[Scorecard], set[str]]] = {
    "overlap": picked,
    "core_overlap": picked_cores,
}

Rows = Sequence[Sequence[Ratio]]


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


def _measure(rows: Rows, chosen: Sequence[int]) -> float | None:
    return mean_of_defined(pooled([row[index] for index in chosen]) for row in rows)


def _rows(run: ScoredRun, occupations: Sequence[str]) -> dict[str, Rows]:
    per_repeat = [{card.occupation: ratios(card) for card in group} for group in run.repeats]
    within = {key: overlaps(run.cards, names) for key, names in OVERLAPS.items()}
    return {
        **{
            key: [[cells[occupation][key] for occupation in occupations] for cells in per_repeat]
            for key in METRICS
        },
        **{
            key: [
                [
                    Ratio(values[occupation], 1) if occupation in values else Ratio(0, 0)
                    for occupation in occupations
                ]
            ]
            for key, values in within.items()
        },
    }


def _interval(old: Rows, new: Rows, samples: Sequence[Sequence[int]]) -> Interval | None:
    differences = []
    for chosen in samples:
        before, after = _measure(old, chosen), _measure(new, chosen)
        if before is None or after is None:
            return None
        differences.append(after - before)
    if not differences:
        return None
    differences.sort()
    cut = round(len(differences) * (1 - CONFIDENCE) / 2)
    return Interval(differences[cut], differences[len(differences) - 1 - cut])


def compare_experiments(
    before: ScoredRun, after: ScoredRun, resamples: int = RESAMPLES, seed: int = SEED
) -> Comparison:
    occupations = sorted(before.occupations & after.occupations)
    everyone = range(len(occupations))
    generator = Random(seed)
    samples = (
        [generator.choices(everyone, k=len(occupations)) for _ in range(resamples)]
        if len(occupations) >= MIN_OCCUPATIONS
        else []
    )
    old, new = _rows(before, occupations), _rows(after, occupations)
    changes = {}
    for key in (*METRICS, *OVERLAPS):
        old_value, new_value = _measure(old[key], everyone), _measure(new[key], everyone)
        interval = (
            None
            if old_value is None or new_value is None
            else _interval(old[key], new[key], samples)
        )
        changes[key] = Change(old_value, new_value, interval)
    return Comparison(len(occupations), changes)
