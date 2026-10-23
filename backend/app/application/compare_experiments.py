from collections.abc import Callable, Sequence, Set
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
    repeats: tuple[int, int]
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


def _mixed(keep: Rows, take: Rows, swap: Sequence[bool]) -> Rows:
    return [
        [taken if flipped else kept for kept, taken, flipped in zip(own, other, swap, strict=True)]
        for own, other in zip(keep, take, strict=True)
    ]


def _p_value(
    old: Rows, new: Rows, swaps: Sequence[Sequence[bool]], observed: float
) -> float | None:
    if len(old) != len(new) or not swaps:
        return None
    everyone = range(len(swaps[0]))
    extreme = 0
    for swap in swaps:
        before = _measure(_mixed(old, new, swap), everyone)
        after = _measure(_mixed(new, old, swap), everyone)
        if before is None or after is None:
            return None
        if abs(after - before) >= abs(observed) - TOLERANCE:
            extreme += 1
    return (extreme + 1) / (len(swaps) + 1)


def _within(run: ScoredRun, repeats: Set[int]) -> ScoredRun:
    kept = tuple(group for group in run.repeats if group[0].repeat in repeats)
    return ScoredRun(kept, len(kept) if run.complete_repeats else 0)


def aligned(before: ScoredRun, after: ScoredRun) -> tuple[ScoredRun, ScoredRun]:
    shared = {group[0].repeat for group in before.repeats} & {
        group[0].repeat for group in after.repeats
    }
    return _within(before, shared), _within(after, shared)


def compare_experiments(
    before: ScoredRun,
    after: ScoredRun,
    resamples: int = RESAMPLES,
    shuffles: int = SHUFFLES,
    seed: int = SEED,
) -> Comparison:
    occupations = sorted(before.occupations & after.occupations)
    everyone = range(len(occupations))
    enough = len(occupations) >= MIN_OCCUPATIONS
    resampler, shuffler = Random(seed), Random(f"{seed} shuffles")
    samples = (
        [resampler.choices(everyone, k=len(occupations)) for _ in range(resamples)]
        if enough
        else []
    )
    swaps = [[shuffler.random() < 0.5 for _ in everyone] for _ in range(shuffles)] if enough else []
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
            _p_value(old[key], new[key], swaps, new_value - old_value),
        )
    return Comparison(len(occupations), (len(before.repeats), len(after.repeats)), changes)
