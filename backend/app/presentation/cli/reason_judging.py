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
    StoredJudgment,
    fleiss_kappa,
    judged_reasons,
    sample_reasons,
    verified_judgments,
)
from app.domain.recommendation import Relevance
from app.presentation.cli.evaluation_data import (
    DEFAULT_DATASET,
    HELDOUT_DATASET,
    UNREADABLE,
    parse_document,
    read_document,
    write_document,
)
from app.presentation.cli.records import digest

DEFAULT_REASON_JUDGMENTS = DEFAULT_DATASET.with_name("reason-judgments.json")
MATERIAL_FILE = "reasons.json"
PROMPT_FILE = "reason-judge-prompt.md"
REPEAT = 1
VOTE_LINES = frozenset({"votes"})
KIND_LABELS = {Relevance.CORE: "柱", Relevance.FOUNDATION: "礎"}
GRADE_LABELS = {
    ReasonGrade.SPECIFIC: "具体的",
    ReasonGrade.VAGUE: "ぼんやり",
    ReasonGrade.ABSENT: "無い",
}
SPLIT_LABELS = {Split.TUNE: "整える用", Split.CHECK: "確かめる用"}


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


def materials(samples: Sequence[SampledReason]) -> list[dict[str, Any]]:
    return [
        {
            "id": sample.key,
            "occupation": sample.case.interpretation,
            "assumption": sample.case.assumption,
            "kind": KIND_LABELS[sample.case.relevance],
            "course": sample.case.course,
            "pillar": sample.case.pillar,
            "reason": sample.case.reason,
        }
        for sample in samples
    ]


def parsed_vote(entry: Mapping[str, Any]) -> ReasonVote:
    grade = entry["grade"]
    if grade not in set(ReasonGrade):
        raise ReasonJudgingError(f"段は {'、'.join(GRADES)} のどれかにしてください: {grade!r}")
    return ReasonVote(ReasonGrade(grade), entry["why"])


def judge_output(document: Mapping[str, Any]) -> dict[str, ReasonVote]:
    votes: dict[str, ReasonVote] = {}
    for entry in document["grades"]:
        if entry["id"] in votes:
            raise ReasonJudgingError(f"同じ理由に 2 つ票があります: {entry['id']}")
        votes[entry["id"]] = parsed_vote(entry)
    return votes


def judged_document(
    run: str, fingerprint: str, model: str, judged: Sequence[JudgedReason]
) -> dict[str, Any]:
    return {
        "run": run,
        "run_fingerprint": fingerprint,
        "repeat": REPEAT,
        "seed": SEED,
        "model": model,
        "prompt": PROMPT_FILE,
        "reasons": [
            {
                "id": reason.sample.key,
                "split": reason.sample.split.value,
                "occupation": reason.sample.case.occupation,
                "interpretation": reason.sample.case.interpretation,
                "assumption": reason.sample.case.assumption,
                "relevance": reason.sample.case.relevance.value,
                "course": reason.sample.case.course,
                "pillar": reason.sample.case.pillar,
                "reason": reason.sample.case.reason,
                "votes": [{"grade": vote.grade.value, "why": vote.why} for vote in reason.votes],
                "answer": reason.answer.value,
            }
            for reason in judged
        ],
    }


def stored_judgment(entry: Mapping[str, Any]) -> StoredJudgment:
    sample = SampledReason(
        entry["id"],
        Split(entry["split"]),
        ReasonCase(
            entry["occupation"],
            entry["interpretation"],
            entry["assumption"],
            Relevance(entry["relevance"]),
            entry["course"],
            entry["pillar"],
            entry["reason"],
        ),
    )
    reason = JudgedReason(sample, tuple(parsed_vote(given) for given in entry["votes"]))
    return StoredJudgment(reason, ReasonGrade(entry["answer"]))


def _samples(path: Path) -> tuple[list[SampledReason], str]:
    try:
        data = path.read_bytes()
        run = parse_document(data)
        occupations = {trial["occupation"] for trial in run["trials"]}
        cases = reason_cases(run)
    except UNREADABLE as error:
        sys.exit(f"実験の結果を読めません: {error!r}")
    try:
        heldout = {
            occupation["name"] for occupation in read_document(HELDOUT_DATASET)["occupations"]
        }
    except UNREADABLE as error:
        sys.exit(f"確かめ用の評価データを読めません: {error!r}")
    if occupations & heldout:
        sys.exit("確かめ用の職業の入った結果は、判定者に見せないので使いません(ADR 0067)")
    try:
        return sample_reasons(cases), digest(data)
    except ReasonJudgingError as error:
        sys.exit(f"理由を取り出せません: {error}")


def _sample(args: argparse.Namespace) -> None:
    samples, _ = _samples(args.run)
    try:
        args.out.mkdir(parents=True, exist_ok=True)
        write_document(args.out / MATERIAL_FILE, materials(samples), frozenset())
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
    samples, fingerprint = _samples(args.run)
    try:
        shown = read_document(args.materials / MATERIAL_FILE)
    except UNREADABLE as error:
        sys.exit(f"判定者に渡した資料を読めません: {error!r}")
    if shown != materials(samples):
        sys.exit(
            "判定者に渡した資料が、この結果から取り直した理由と違います"
            "(sample から作り直して判定し直す)"
        )
    try:
        outputs = [judge_output(read_document(path)) for path in args.votes]
        judged = judged_reasons(samples, outputs)
    except ReasonJudgingError as error:
        sys.exit(f"判定者の出力が決まりに合いません: {error}")
    except UNREADABLE as error:
        sys.exit(f"判定者の出力を読めません: {error!r}")
    document = judged_document(args.run.name, fingerprint, args.model, judged)
    try:
        write_document(args.out, document, VOTE_LINES)
    except OSError as error:
        sys.exit(f"書けません: {error}")
    print("\n".join([f"{args.out} に正解をまとめた", *summary(judged)]))


def _check(args: argparse.Namespace) -> None:
    samples, fingerprint = _samples(args.run)
    try:
        document = read_document(args.judgments)
        made_from = {key: document[key] for key in ("run", "run_fingerprint", "seed", "repeat")}
        prompt = document["prompt"]
        stored = [stored_judgment(entry) for entry in document["reasons"]]
    except ReasonJudgingError as error:
        sys.exit(f"正解の票が決まりに合いません: {error}")
    except UNREADABLE as error:
        sys.exit(f"正解を読めません: {error!r}")
    expected = {
        "run": args.run.name,
        "run_fingerprint": fingerprint,
        "seed": SEED,
        "repeat": REPEAT,
    }
    if made_from != expected:
        sys.exit(f"正解は別の結果か取り出し方から作っています: {made_from}")
    if prompt != PROMPT_FILE:
        sys.exit(f"正解は別の指示文で付けています: {prompt}")
    try:
        judged = verified_judgments(samples, stored)
    except ReasonJudgingError as error:
        sys.exit(f"正解が結果から取り直した理由と合いません: {error}")
    print("\n".join([f"{args.judgments} は {args.run.name} の理由と合う", *summary(judged)]))


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
    merge.add_argument("--materials", type=Path, required=True)
    merge.add_argument("--votes", type=Path, nargs="+", required=True)
    merge.add_argument("--model", required=True)
    merge.add_argument("--out", type=Path, required=True)
    merge.set_defaults(handle=_merge)
    check = commands.add_parser(
        "check", help="正解が実験の結果から取り直した理由と合うかを確かめ、正解の数を出す"
    )
    check.add_argument("run", type=Path)
    check.add_argument("--judgments", type=Path, default=DEFAULT_REASON_JUDGMENTS)
    check.set_defaults(handle=_check)
    args = parser.parse_args(argv)
    args.handle(args)


if __name__ == "__main__":
    main()
