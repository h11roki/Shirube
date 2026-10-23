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
SHUFFLES = 10_000
SEED = 0
CONFIDENCE = 0.95
SIGNIFICANCE = 0.05
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


@dataclass(frozen=True)
class Change:
    before: float | None
    after: float | None
    interval: Interval | None
    p_value: float | None

    @property
    def difference(self) -> float | None:
        if self.before is None or self.after is None:
            return None
        return self.after - self.before

    @property
    def clear(self) -> bool:
        return self.p_value is not None and self.p_value < SIGNIFICANCE


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


def _by_occupation(rows: Rows) -> list[Ratio]:
    return [
        Ratio(sum(cell.numerator for cell in cells), sum(cell.denominator for cell in cells))
        for cells in zip(*rows, strict=True)
    ]


def _p_value(old: Rows, new: Rows, swaps: Sequence[Sequence[bool]]) -> float | None:
    first, second = _by_occupation(old), _by_occupation(new)
    before, after = pooled(first), pooled(second)
    if not swaps or before is None or after is None:
        return None
    observed = abs(after - before)
    extreme = 0
    for swap in swaps:
        sides = [
            (taken, kept) if flipped else (kept, taken)
            for kept, taken, flipped in zip(first, second, swap, strict=True)
        ]
        shuffled_before = pooled([pair[0] for pair in sides])
        shuffled_after = pooled([pair[1] for pair in sides])
        if shuffled_before is None or shuffled_after is None:
            return None
        if abs(shuffled_after - shuffled_before) >= observed - TOLERANCE:
            extreme += 1
    return (extreme + 1) / (len(swaps) + 1)


def compare_experiments(
    before: ScoredRun,
    after: ScoredRun,
    resamples: int = RESAMPLES,
    shuffles: int = SHUFFLES,
    seed: int = SEED,
) -> Comparison:
    occupations = sorted(before.occupations & after.occupations)
    everyone = range(len(occupations))
    generator = Random(seed)
    enough = len(occupations) >= MIN_OCCUPATIONS
    samples = (
        [generator.choices(everyone, k=len(occupations)) for _ in range(resamples)]
        if enough
        else []
    )
    swaps = (
        [[generator.random() < 0.5 for _ in everyone] for _ in range(shuffles)] if enough else []
    )
    old, new = _rows(before, occupations), _rows(after, occupations)
    changes = {}
    for key in (*METRICS, *OVERLAPS):
        old_value, new_value = _measure(old[key], everyone), _measure(new[key], everyone)
        if old_value is None or new_value is None:
            changes[key] = Change(old_value, new_value, None, None)
            continue
        changes[key] = Change(
            old_value,
            new_value,
            _interval(old[key], new[key], samples),
            _p_value(old[key], new[key], swaps),
        )
    return Comparison(len(occupations), changes)
