import argparse
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.application.reason_judging import (
    GRADES,
    SEED,
    JudgedReason,
    ReasonCase,
    ReasonGrade,
    ReasonJudgingError,
    ReasonVote,
    SampledReason,
    Split,
    fleiss_kappa,
    judged_reasons,
    sample_reasons,
)
from app.domain.recommendation import Relevance
from app.presentation.cli.evaluation_data import (
    DEFAULT_DATASET,
    HELDOUT_DATASET,
    read_document,
    write_document,
)
from app.presentation.cli.records import digest

DEFAULT_REASON_JUDGMENTS = DEFAULT_DATASET.with_name("reason-judgments.json")
MATERIAL_FILE = "reasons.json"
PROMPT_FILE = "reason-judge-prompt.md"
JUDGE_MODEL = "Claude Opus 5.5(Claude Code のサブエージェント)"
REPEAT = 1
KIND_LABELS = {Relevance.CORE: "柱", Relevance.FOUNDATION: "礎"}
GRADE_LABELS = {
    ReasonGrade.SPECIFIC: "具体的",
    ReasonGrade.VAGUE: "ぼんやり",
    ReasonGrade.ABSENT: "無い",
}
SPLIT_LABELS = {Split.TUNE: "整える用", Split.CHECK: "確かめる用"}
UNREADABLE = (OSError, ValueError, KeyError, TypeError, AttributeError)


def reason_cases(run: Mapping[str, Any]) -> list[ReasonCase]:
    return [
        ReasonCase(
            trial["occupation"],
            trial["interpretation"],
            trial["assumption"],
            Relevance(course["relevance"]),
            course["name"],
            course["prerequisite_for"],
            course["reason"],
        )
        for trial in run["trials"]
        if "failure" not in trial and trial["repeat"] == REPEAT
        for course in trial["courses"]
    ]


def material(sample: SampledReason) -> dict[str, Any]:
    case = sample.case
    return {
        "id": sample.key,
        "occupation": case.interpretation,
        "assumption": case.assumption,
        "kind": KIND_LABELS[case.relevance],
        "course": case.course,
        "pillar": case.pillar,
        "reason": case.reason,
    }


def judge_output(document: Mapping[str, Any]) -> dict[str, ReasonVote]:
    votes: dict[str, ReasonVote] = {}
    for entry in document["grades"]:
        if entry["id"] in votes:
            raise ReasonJudgingError(f"同じ理由に 2 つ票があります: {entry['id']}")
        votes[entry["id"]] = ReasonVote(ReasonGrade(entry["grade"]), entry["why"])
    return votes


def sampled_entry(sample: SampledReason) -> dict[str, Any]:
    case = sample.case
    return {
        "id": sample.key,
        "split": sample.split.value,
        "occupation": case.occupation,
        "interpretation": case.interpretation,
        "assumption": case.assumption,
        "relevance": case.relevance.value,
        "course": case.course,
        "pillar": case.pillar,
        "reason": case.reason,
    }


def judged_document(run: Path, judged: Sequence[JudgedReason]) -> dict[str, Any]:
    return {
        "run": run.name,
        "run_fingerprint": digest(run.read_bytes()),
        "repeat": REPEAT,
        "seed": SEED,
        "model": JUDGE_MODEL,
        "prompt": PROMPT_FILE,
        "reasons": [
            {
                **sampled_entry(reason.sample),
                "votes": [{"grade": vote.grade.value, "why": vote.why} for vote in reason.votes],
                "answer": reason.answer.value,
            }
            for reason in judged
        ],
    }


def judged_from(
    document: Mapping[str, Any], samples: Sequence[SampledReason]
) -> list[JudgedReason]:
    entries = document["reasons"]
    if [entry["id"] for entry in entries] != [sample.key for sample in samples]:
        raise ReasonJudgingError(
            "理由の番号が、結果から取り直した理由の番号と同じ順に並んでいません"
        )
    judged = []
    for entry, sample in zip(entries, samples, strict=True):
        expected = sampled_entry(sample)
        if {key: entry[key] for key in expected} != expected:
            raise ReasonJudgingError(f"{sample.key}: 結果から取り直した理由と違います")
        reason = JudgedReason(
            sample,
            tuple(ReasonVote(ReasonGrade(vote["grade"]), vote["why"]) for vote in entry["votes"]),
        )
        if reason.answer.value != entry["answer"]:
            raise ReasonJudgingError(f"{sample.key}: 正解が 3 票の中央値ではありません")
        judged.append(reason)
    return judged


def _samples(path: Path) -> list[SampledReason]:
    try:
        run = read_document(path)
        heldout = {
            occupation["name"] for occupation in read_document(HELDOUT_DATASET)["occupations"]
        }
        cases = reason_cases(run)
    except UNREADABLE as error:
        sys.exit(f"実験の結果を読めません: {error!r}")
    if any(case.occupation in heldout for case in cases):
        sys.exit("確かめ用の職業の入った結果は、判定者に見せないので使いません(ADR 0067)")
    try:
        return sample_reasons(cases)
    except ReasonJudgingError as error:
        sys.exit(f"理由を取り出せません: {error}")


def _sample(args: argparse.Namespace) -> None:
    samples = _samples(args.run)
    try:
        args.out.mkdir(parents=True, exist_ok=True)
        write_document(
            args.out / MATERIAL_FILE,
            [material(sample) for sample in samples],
            frozenset(),
        )
    except OSError as error:
        sys.exit(f"書けません: {error}")
    counts = Counter(sample.split for sample in samples)
    print(
        f"{args.out / MATERIAL_FILE} に理由 {len(samples)} 件を混ぜた順に書いた("
        + "、".join(f"{SPLIT_LABELS[split]} {counts[split]}" for split in Split)
        + ")"
    )


def summary(judged: Sequence[JudgedReason]) -> list[str]:
    lines = []
    for relevance, label in KIND_LABELS.items():
        chosen = [reason for reason in judged if reason.sample.case.relevance is relevance]
        kappa = fleiss_kappa([[vote.grade for vote in reason.votes] for reason in chosen])
        lines.append(
            f"{label} {len(chosen)} 件(3 体の一致 Fleiss の κ "
            + ("-" if kappa is None else f"{kappa:.2f}")
            + ")"
        )
        for split in Split:
            answers = Counter(reason.answer for reason in chosen if reason.sample.split is split)
            lines.append(
                f"  {SPLIT_LABELS[split]}: "
                + "、".join(f"{GRADE_LABELS[grade]} {answers[grade]}" for grade in reversed(GRADES))
            )
    return lines


def _merge(args: argparse.Namespace) -> None:
    samples = _samples(args.run)
    try:
        outputs = [judge_output(read_document(path)) for path in args.votes]
        judged = judged_reasons(samples, outputs)
    except ReasonJudgingError as error:
        sys.exit(f"判定者の出力が決まりに合いません: {error}")
    except UNREADABLE as error:
        sys.exit(f"判定者の出力を読めません: {error!r}")
    try:
        write_document(args.out, judged_document(args.run, judged), frozenset({"votes"}))
    except OSError as error:
        sys.exit(f"書けません: {error}")
    print("\n".join([f"{args.out} に正解をまとめた", *summary(judged)]))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="理由の文の正解を作る資料を書き、判定をまとめる")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser(
        "sample", help="実験の結果から判定する理由を取り出し、判定者に渡す資料を書く"
    )
    sample.add_argument("run", type=Path)
    sample.add_argument("--out", type=Path, required=True)
    sample.set_defaults(handle=_sample)
    merge = commands.add_parser("merge", help="判定者 3 体の出力を正解にまとめる")
    merge.add_argument("run", type=Path)
    merge.add_argument("--votes", type=Path, nargs="+", required=True)
    merge.add_argument("--out", type=Path, default=DEFAULT_REASON_JUDGMENTS)
    merge.set_defaults(handle=_merge)
    args = parser.parse_args(argv)
    args.handle(args)


if __name__ == "__main__":
    main()
