from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from random import Random

from app.domain.recommendation import Relevance

SEED = 0
JUDGES = 3
PER_SPLIT = {Relevance.CORE: 38, Relevance.FOUNDATION: 37}
WHY_LENGTH = 60


class ReasonJudgingError(ValueError):
    pass


class ReasonGrade(StrEnum):
    ABSENT = "absent"
    VAGUE = "vague"
    SPECIFIC = "specific"


GRADES = tuple(ReasonGrade)


class Split(StrEnum):
    TUNE = "tune"
    CHECK = "check"


@dataclass(frozen=True)
class ReasonCase:
    occupation: str
    interpretation: str
    assumption: str | None
    relevance: Relevance
    course: str
    pillar: str | None
    reason: str


@dataclass(frozen=True)
class SampledReason:
    key: str
    split: Split
    case: ReasonCase


@dataclass(frozen=True)
class ReasonVote:
    grade: ReasonGrade
    why: str

    def __post_init__(self) -> None:
        if not 0 < len(self.why) <= WHY_LENGTH:
            raise ReasonJudgingError(f"根拠は 1〜{WHY_LENGTH} 字にしてください: {self.why!r}")


@dataclass(frozen=True)
class JudgedReason:
    sample: SampledReason
    votes: tuple[ReasonVote, ...]

    def __post_init__(self) -> None:
        if len(self.votes) != JUDGES:
            raise ReasonJudgingError(f"{self.sample.key}: 票は {JUDGES} つにしてください")

    @property
    def answer(self) -> ReasonGrade:
        ranked = sorted((vote.grade for vote in self.votes), key=GRADES.index)
        return ranked[len(ranked) // 2]


@dataclass(frozen=True)
class StoredJudgment:
    reason: JudgedReason
    answer: ReasonGrade


def sample_reasons(cases: Sequence[ReasonCase], seed: int = SEED) -> list[SampledReason]:
    occupations = sorted({case.occupation for case in cases})
    Random(seed).shuffle(occupations)
    half = len(occupations) // 2
    splits = {Split.TUNE: set(occupations[:half]), Split.CHECK: set(occupations[half:])}
    picker = Random(f"{seed} reasons")
    picked: list[tuple[Split, ReasonCase]] = []
    for split, members in splits.items():
        for relevance, count in PER_SPLIT.items():
            pool = [
                case for case in cases if case.occupation in members and case.relevance is relevance
            ]
            if len(pool) < count:
                raise ReasonJudgingError(
                    f"{split} の職業の {relevance} の理由が {count} 件に足りません: {len(pool)} 件"
                )
            picked += [(split, case) for case in picker.sample(pool, count)]
    picker.shuffle(picked)
    return [
        SampledReason(f"r{number:03d}", split, case)
        for number, (split, case) in enumerate(picked, 1)
    ]


def judged_reasons(
    samples: Sequence[SampledReason], outputs: Sequence[Mapping[str, ReasonVote]]
) -> list[JudgedReason]:
    if len(outputs) != JUDGES:
        raise ReasonJudgingError(f"判定者の出力を {JUDGES} つ渡してください: {len(outputs)} つ")
    keys = {sample.key for sample in samples}
    for number, output in enumerate(outputs, 1):
        if output.keys() != keys:
            missing = sorted(keys - output.keys())
            extra = sorted(output.keys() - keys)
            raise ReasonJudgingError(
                f"{number} つ目の判定者の出力の理由がそろっていません"
                f"(足りない: {'、'.join(missing) or 'なし'}、多い: {'、'.join(extra) or 'なし'})"
            )
    return [
        JudgedReason(sample, tuple(output[sample.key] for output in outputs)) for sample in samples
    ]


def verified_judgments(
    samples: Sequence[SampledReason], stored: Sequence[StoredJudgment]
) -> list[JudgedReason]:
    if [judgment.reason.sample.key for judgment in stored] != [sample.key for sample in samples]:
        raise ReasonJudgingError(
            "理由の番号が、結果から取り直した理由の番号と同じ順に並んでいません"
        )
    for judgment, sample in zip(stored, samples, strict=True):
        if judgment.reason.sample != sample:
            raise ReasonJudgingError(f"{sample.key}: 結果から取り直した理由と違います")
        if judgment.reason.answer is not judgment.answer:
            raise ReasonJudgingError(f"{sample.key}: 正解が 3 票の中央値ではありません")
    return [judgment.reason for judgment in stored]


def fleiss_kappa(ratings: Sequence[Sequence[ReasonGrade]]) -> float | None:
    raters = {len(row) for row in ratings}
    if len(raters) != 1 or (count := raters.pop()) < 2:
        raise ReasonJudgingError("どの理由にも同じ数の 2 つ以上の票が要ります")
    tallies = [[row.count(grade) for grade in GRADES] for row in ratings]
    shares = [
        sum(row[index] for row in tallies) / (len(ratings) * count) for index in range(len(GRADES))
    ]
    chance = sum(share * share for share in shares)
    if chance == 1:
        return None
    observed = sum(
        (sum(tally**2 for tally in row) - count) / (count * (count - 1)) for row in tallies
    ) / len(tallies)
    return (observed - chance) / (1 - chance)
