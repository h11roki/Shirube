import argparse
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.application.compare_experiments import MIN_OCCUPATIONS
from app.application.compare_reason_judgments import compare_shares
from app.application.reason_judging import (
    GRADES,
    KIND_LABELS,
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
from app.domain.recommendation import REASON_LIMIT, Relevance
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
PROMPT = DEFAULT_DATASET.with_name("reason-judge-prompt.md")
INSTRUCTIONS_HEADING = "\n## 指示文\n"
REPEAT = 1
VOTE_LINES = frozenset({"votes"})
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
    grade, why = entry["grade"], entry["why"]
    if not isinstance(grade, str) or grade not in set(ReasonGrade):
        raise ReasonJudgingError(f"段は {'、'.join(GRADES)} のどれかにしてください: {grade!r}")
    if not isinstance(why, str):
        raise ReasonJudgingError(f"根拠は文字列にしてください: {why!r}")
    return ReasonVote(ReasonGrade(grade), why)


def instructions_fingerprint() -> str:
    _, heading, instructions = PROMPT.read_text(encoding="utf-8").partition(INSTRUCTIONS_HEADING)
    if not heading:
        raise ValueError(f"{PROMPT.name} に「指示文」の節がありません")
    return digest(instructions.encode())


def judge_output(document: Mapping[str, Any]) -> dict[str, ReasonVote]:
    votes: dict[str, ReasonVote] = {}
    for entry in document["grades"]:
        if entry["id"] in votes:
            raise ReasonJudgingError(f"同じ理由に 2 つ票があります: {entry['id']}")
        votes[entry["id"]] = parsed_vote(entry)
    return votes


def judged_document(
    run: str, fingerprint: str, model: str, prompt: str, judged: Sequence[JudgedReason]
) -> dict[str, Any]:
    return {
        "run": run,
        "run_fingerprint": fingerprint,
        "repeat": REPEAT,
        "seed": SEED,
        "model": model,
        "prompt": PROMPT.name,
        "prompt_fingerprint": prompt,
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


def _samples(path: Path) -> tuple[list[SampledReason], list[ReasonCase], str]:
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
        return sample_reasons(cases, occupations), cases, digest(data)
    except ReasonJudgingError as error:
        sys.exit(f"理由を取り出せません: {error}")


def _sample(args: argparse.Namespace) -> None:
    samples, _, _ = _samples(args.run)
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
        answers = Counter(reason.answer for reason in chosen)
        lines.append(
            f"{label} {len(chosen)} 件: "
            + "、".join(f"{GRADE_LABELS[grade]} {answers[grade]}" for grade in reversed(GRADES))
            + "(3 体の一致 Fleiss の κ "
            + ("-" if kappa is None else f"{kappa:.2f}")
            + ")"
        )
    return lines


def _merge(args: argparse.Namespace) -> None:
    samples, _, fingerprint = _samples(args.run)
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
    try:
        prompt = instructions_fingerprint()
    except UNREADABLE as error:
        sys.exit(f"判定者の指示文を読めません: {error!r}")
    document = judged_document(args.run.name, fingerprint, args.model, prompt, judged)
    try:
        write_document(args.out, document, VOTE_LINES)
    except OSError as error:
        sys.exit(f"書けません: {error}")
    print("\n".join([f"{args.out} に正解をまとめた", *summary(judged)]))


@dataclass(frozen=True)
class VerifiedSide:
    name: str
    judged: list[JudgedReason]
    cases: list[ReasonCase]
    fingerprint: str
    model: str


def verified_side(run: Path, judgments: Path) -> VerifiedSide:
    samples, cases, fingerprint = _samples(run)
    try:
        expected = {
            "run_fingerprint": fingerprint,
            "seed": SEED,
            "repeat": REPEAT,
            "prompt_fingerprint": instructions_fingerprint(),
        }
        document = read_document(judgments)
        differing = [key for key, value in expected.items() if document[key] != value]
        model = str(document["model"])
        stored = [stored_judgment(entry) for entry in document["reasons"]]
    except ReasonJudgingError as error:
        sys.exit(f"正解の票が決まりに合いません: {error}")
    except UNREADABLE as error:
        sys.exit(f"正解か判定者の指示文を読めません: {error!r}")
    if differing:
        sys.exit(
            "正解は、今の結果、取り出し方、判定者の指示文と違うもとから作っています: "
            + "、".join(differing)
        )
    try:
        judged = verified_judgments(samples, stored)
    except ReasonJudgingError as error:
        sys.exit(f"正解が結果から取り直した理由と合いません: {error}")
    return VerifiedSide(str(run), judged, cases, fingerprint, model)


def verified_answers(run: Path, judgments: Path) -> list[JudgedReason]:
    return verified_side(run, judgments).judged


def compare_lines(before: VerifiedSide, after: VerifiedSide) -> list[str]:
    shared = {case.occupation for case in before.cases} & {case.occupation for case in after.cases}
    old = [reason for reason in before.judged if reason.sample.case.occupation in shared]
    new = [reason for reason in after.judged if reason.sample.case.occupation in shared]
    left_out = len(before.judged) - len(old) + len(after.judged) - len(new)
    comparison = compare_shares(old, new, shared)
    lines = [f"理由の文の比べ(前 {before.name}、後 {after.name})"]
    if before.model == after.model:
        lines.append(f"  判定者: {before.model}(前と後で同じ)")
    else:
        lines.append(
            f"  判定者: 前 {before.model}、後 {after.model}(違うので、差には判定者の違いも入る)"
        )
    lines.append(
        f"  両方の結果にそろった職業 {comparison.occupations} で区間を出す"
        + (f"(そろっていない職業の理由 {left_out} 件は外した)" if left_out else "")
    )
    for relevance, label in KIND_LABELS.items():
        old_counts = Counter(r.answer for r in old if r.sample.case.relevance is relevance)
        new_counts = Counter(r.answer for r in new if r.sample.case.relevance is relevance)
        lines.append(f"  {label} {old_counts.total()} 件 → {new_counts.total()} 件")
        for grade in reversed(GRADES):
            change = comparison.changes[relevance][grade]
            shown = [
                f"{count}({share:.1%})" if share is not None else f"{count}(-)"
                for count, share in (
                    (old_counts[grade], change.before),
                    (new_counts[grade], change.after),
                )
            ]
            line = f"    {GRADE_LABELS[grade]} {shown[0]} → {shown[1]}"
            if change.difference is not None:
                line += f"、{change.difference * 100:+.1f} ポイント"
            if change.interval is not None:
                line += (
                    f"(95% 区間 {change.interval.low * 100:+.1f}〜"
                    f"{change.interval.high * 100:+.1f}、"
                    + ("差あり" if change.clear else "はっきりしない")
                    + ")"
                )
            elif change.difference is not None:
                line += (
                    "(区間は出さない: 選び直すと片側に理由が無い組があった)"
                    if comparison.enough
                    else f"(区間は出さない: そろった職業が {MIN_OCCUPATIONS} に満たない)"
                )
            lines.append(line)
    long_shown = []
    for name, side in (("前", before), ("後", after)):
        long = sum(1 for case in side.cases if len(case.reason) > REASON_LIMIT)
        share = f"({long / len(side.cases):.1%})" if side.cases else ""
        long_shown.append(f"{name} {long} / {len(side.cases)}{share}")
    lines.append(f"  {REASON_LIMIT} 字を超える理由(1 回目の推薦): " + "、".join(long_shown))
    return lines


def _compare(args: argparse.Namespace) -> None:
    before, after = (verified_side(run, judgments) for run, judgments in (args.before, args.after))
    if before.fingerprint == after.fingerprint:
        sys.exit("前と後に同じ実験の結果を渡しています")
    try:
        print("\n".join(compare_lines(before, after)))
    except ReasonJudgingError as error:
        sys.exit(f"前と後を比べられません: {error}")


def _check(args: argparse.Namespace) -> None:
    judged = verified_answers(args.run, args.judgments)
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
    compare = commands.add_parser(
        "compare", help="前と後の正解を並べ、段の割合の差を職業を選び直す区間つきで出す"
    )
    for side in ("--before", "--after"):
        compare.add_argument(
            side, type=Path, nargs=2, required=True, metavar=("実験の結果", "正解")
        )
    compare.set_defaults(handle=_compare)
    args = parser.parse_args(argv)
    args.handle(args)


if __name__ == "__main__":
    main()
