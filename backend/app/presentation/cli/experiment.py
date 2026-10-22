import argparse
import hashlib
import json
import math
import re
import signal
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.evaluate_search import RECALL_CUTOFFS, EvaluationDataset, EvaluationError
from app.application.evaluate_selection import HandwrittenProfiles
from app.application.ports import TokenUsage
from app.application.run_experiment import (
    ExperimentSummary,
    FailedTrial,
    RunExperiment,
    Spread,
    Trial,
    summarize,
)
from app.application.search_courses import SearchError
from app.domain.course import UNIVERSITY_TIME
from app.domain.occupation import OccupationProfileError
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.llm import openai_course_selector as selection_prompt
from app.infrastructure.llm import openai_occupation_analyzer as occupation_prompt
from app.infrastructure.llm.usage_meter import LangChainUsageMeter
from app.presentation.cli.evaluation_data import (
    DEFAULT_DATASET,
    DEFAULT_JUDGMENTS,
    load_dataset,
    load_judgments,
)
from app.presentation.composition import (
    database_engine,
    load_settings,
    openai_course_selector,
    openai_occupation_analyzer,
    search_courses,
)
from app.settings import Settings

RUNS = DEFAULT_DATASET.with_name("runs")
PRICES = {
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
}
YEN_PER_DOLLAR = 150
FAILURE_STREAK_LIMIT = 3
PROFILES = ("analyzed", "handwritten")
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
METRICS = (
    *((f"recall@{cutoff}", f"検索の再現率 @{cutoff}", "ratio") for cutoff in RECALL_CUTOFFS),
    ("candidate_recall", "選び直しに渡した候補の再現率", "ratio"),
    ("core_precision", "中心の適合率", "ratio"),
    ("expected_as_core", "期待する科目を中心に選んだ割合", "ratio"),
    ("unrelated", "選んだ科目のうち関係なし", "ratio"),
    ("cores", "1 職業に選んだ中心", "count"),
    ("foundations", "1 職業に選んだ土台", "count"),
)


def price_of(model: str) -> tuple[float, float, float] | None:
    return next((rates for name, rates in PRICES.items() if model.startswith(name)), None)


def yen(usage: Mapping[str, TokenUsage]) -> float:
    total = 0.0
    for model, tokens in usage.items():
        price = price_of(model)
        if price is None:
            continue
        fresh, cached, output = price
        total += (
            (tokens.input - tokens.cached) * fresh + tokens.cached * cached + tokens.output * output
        ) / 1_000_000
    return total * YEN_PER_DOLLAR


def unpriced(models: Sequence[str]) -> list[str]:
    return sorted(model for model in models if price_of(model) is None)


def label(text: str) -> str:
    if not LABEL.fullmatch(text):
        raise argparse.ArgumentTypeError("英数字と . _ - だけで、英数字から始めてください")
    return text


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:8]


def _commit() -> str | None:
    here = Path(__file__).resolve().parent
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=here, capture_output=True, check=True
        ).stdout
        changes = subprocess.run(
            ["git", "diff", "HEAD"], cwd=here, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    commit = head.decode().strip()
    return f"{commit}-dirty-{_digest(changes)}" if changes else commit


@dataclass(frozen=True)
class Collection:
    outcomes: list[Trial | FailedTrial]
    stopped: str | None
    over_budget: bool


def collect(
    outcomes: Iterator[Trial | FailedTrial],
    total: int,
    budget: float,
    spent: Callable[[], dict[str, TokenUsage]],
) -> Collection:
    collected: list[Trial | FailedTrial] = []
    streak = 0
    try:
        for outcome in outcomes:
            collected.append(outcome)
            streak = streak + 1 if isinstance(outcome, FailedTrial) else 0
            usage = spent()
            detail = (
                f"{outcome.seconds.total:.1f} 秒"
                if isinstance(outcome, Trial)
                else f"失敗: {outcome.failure}"
            )
            print(
                f"{len(collected)}/{total} {outcome.occupation}({outcome.repeat} 回目)"
                f"{yen(outcome.usage):.2f} 円、{detail}、ここまで {yen(usage):.1f} 円",
                file=sys.stderr,
            )
            if missing := unpriced(list(usage)):
                return Collection(
                    collected, f"料金表に無いモデルが答えた: {'、'.join(missing)}", False
                )
            if streak >= FAILURE_STREAK_LIMIT:
                return Collection(collected, f"推薦が {streak} 回続けて失敗した", False)
            if yen(usage) >= budget and len(collected) < total:
                return Collection(collected, f"費用の上限 {budget:g} 円に達した", True)
    except EvaluationError as error:
        return Collection(collected, f"評価データが合わない: {error}", False)
    except SearchError as error:
        return Collection(collected, str(error), False)
    except OperationalError as error:
        return Collection(collected, f"DB に接続できません: {error.orig}", False)
    except SQLAlchemyError as error:
        return Collection(collected, f"DB の操作に失敗しました: {error}", False)
    except OSError as error:
        return Collection(collected, f"ネットワークに失敗しました: {error}", False)
    except KeyboardInterrupt:
        return Collection(collected, "中断した", False)
    return Collection(collected, None, False)


def summary_document(summary: ExperimentSummary) -> dict[str, Any]:
    metrics: dict[str, Spread | None] = {
        **{
            f"recall@{cutoff}": value
            for cutoff, value in zip(RECALL_CUTOFFS, summary.recall, strict=True)
        },
        "candidate_recall": summary.candidate_recall,
        "core_precision": summary.core_precision,
        "expected_as_core": summary.expected_as_core,
        "unrelated": summary.unrelated,
        "cores": summary.cores,
        "foundations": summary.foundations,
    }
    return {
        "trials": summary.trials,
        "failures": summary.failures,
        "complete_repeats": summary.complete_repeats,
        "scored_repeats": summary.scored_repeats,
        **{key: None if value is None else asdict(value) for key, value in metrics.items()},
        "overlap": summary.overlap,
        "core_overlap": summary.core_overlap,
        "yen_per_plan": yen(summary.usage) / summary.trials,
        "tokens_per_plan": {
            model: {
                "input": tokens.input / summary.trials,
                "cached": tokens.cached / summary.trials,
                "output": tokens.output / summary.trials,
            }
            for model, tokens in summary.usage.items()
        },
        "seconds": asdict(summary.seconds) | {"total": summary.seconds.total},
    }


def trial_document(outcome: Trial | FailedTrial) -> dict[str, Any]:
    if isinstance(outcome, FailedTrial):
        return asdict(outcome)
    judged = {pick.name: pick.judgment.value for pick in outcome.result.picks}
    return {
        "occupation": outcome.occupation,
        "repeat": outcome.repeat,
        "interpretation": outcome.profile.interpretation,
        "assumption": outcome.profile.assumption,
        "skills": list(outcome.profile.skills),
        "candidates": list(outcome.candidates),
        "courses": [
            {
                "name": course.name,
                "relevance": course.relevance.value,
                "judgment": judged[course.name],
                "reason": course.reason,
                "prerequisite_for": course.prerequisite_for,
            }
            for course in outcome.courses
        ],
        "unlinked": [
            {
                "name": pick.name,
                "prerequisite_for": pick.prerequisite_for,
                "judgment": pick.judgment.value,
            }
            for pick in outcome.result.unlinked
        ],
        "expected": [
            {
                "name": course.name,
                "picked": None if course.picked is None else course.picked.value,
                "searched": course.searched,
                "unlinked": course.unlinked,
            }
            for course in outcome.result.expected
        ],
        "usage": {model: asdict(tokens) for model, tokens in outcome.usage.items()},
        "seconds": asdict(outcome.seconds),
    }


def _format(kind: str, value: Mapping[str, float] | None) -> str:
    if value is None:
        return "-"
    if kind == "ratio":
        return (
            f"{value['mean']:.0%} ± {value['std'] * 100:.0f}"
            f"({value['low']:.0%}〜{value['high']:.0%})"
        )
    return f"{value['mean']:.2f} ± {value['std']:.2f}({value['low']:.2f}〜{value['high']:.2f})"


def _counts(summary: Mapping[str, Any]) -> str:
    return (
        f"推薦 {summary['trials']} 回、失敗 {summary['failures']} 回、"
        f"全職業がそろった回 {summary['complete_repeats']}、採点した回 {summary['scored_repeats']}"
    )


def render(document: Mapping[str, Any]) -> str:
    config, summary = document["config"], document["summary"]
    lines = [
        f"実験 {document['label']}({document['created']}、commit {document['commit']}、"
        f"{config['occupations']} 職業 × {config['repeats']} 回、"
        f"職業の読み取り {config['profiles']}、"
        f"{config['chat_model']} / {config['selection_model']}、候補 {config['candidate_limit']})",
    ]
    if document["stopped"] is not None:
        lines.append(f"  途中で止めた: {document['stopped']}")
    lines.append(f"  使った費用 {document['spent_yen']:.1f} 円")
    if summary is None:
        lines.append("  推薦が全て失敗したので集計していない")
        return "\n".join(lines)
    lines.append(f"  {_counts(summary)}")
    lines += [f"  {name} {_format(kind, summary.get(key))}" for key, name, kind in METRICS]
    if summary["overlap"] is not None:
        lines.append(
            f"  揺れ(同じ職業の回どうしの重なり)選んだ科目 {summary['overlap']:.2f}、"
            f"中心 {summary['core_overlap']:.2f}"
        )
    tokens = "、".join(
        f"{model} 入力 {usage['input']:,.0f}(キャッシュ {usage['cached']:,.0f})"
        f"/ 出力 {usage['output']:,.0f}"
        for model, usage in summary["tokens_per_plan"].items()
    )
    seconds = summary["seconds"]
    lines.append(f"  1 回の推薦あたり {summary['yen_per_plan']:.2f} 円({tokens})")
    lines.append(
        f"  1 回の推薦の時間 {seconds['total']:.1f} 秒(読み取り {seconds['reading']:.1f}、"
        f"検索 {seconds['searching']:.1f}、選び直し {seconds['selecting']:.1f})"
    )
    return "\n".join(lines)


def compare(before: Mapping[str, Any], after: Mapping[str, Any]) -> str:
    old_summary, new_summary = before["summary"], after["summary"]
    lines = [f"比べる: {before['label']} → {after['label']}"]
    for run in (before, after):
        stopped = "" if run["stopped"] is None else f"、途中で止めた({run['stopped']})"
        lines.append(f"  {run['label']}: {_counts(run['summary'])}{stopped}")
    old_config = before["config"] | {"commit": before["commit"]}
    new_config = after["config"] | {"commit": after["commit"]}
    differences = [
        f"{key} {old_config.get(key)} → {new_config.get(key)}"
        for key in sorted(old_config.keys() | new_config.keys())
        if old_config.get(key) != new_config.get(key)
    ]
    if differences:
        lines.append(f"  設定の違い: {'、'.join(differences)}")
    judged = old_summary["scored_repeats"] > 1 and new_summary["scored_repeats"] > 1
    for key, name, kind in METRICS:
        old, new = old_summary.get(key), new_summary.get(key)
        if old is None or new is None:
            lines.append(f"  {name}: {_format(kind, old)} → {_format(kind, new)}")
            continue
        delta = new["mean"] - old["mean"]
        noise = max(old["std"], new["std"])
        verdict = ("揺れより大きい" if abs(delta) > noise else "揺れの範囲") if judged else "-"
        difference = f"{delta * 100:+.0f} ポイント" if kind == "ratio" else f"{delta:+.2f}"
        lines.append(
            f"  {name}: {_format(kind, old)} → {_format(kind, new)}、差 {difference}、{verdict}"
        )
    for key, name in (
        ("overlap", "揺れ(選んだ科目の重なり)"),
        ("core_overlap", "揺れ(中心の重なり)"),
    ):
        old, new = old_summary[key], new_summary[key]
        if old is not None and new is not None:
            lines.append(f"  {name}: {old:.2f} → {new:.2f}、差 {new - old:+.2f}")
    lines.append(
        f"  1 回の推薦あたりの費用: {old_summary['yen_per_plan']:.2f} 円 → "
        f"{new_summary['yen_per_plan']:.2f} 円"
    )
    lines.append(
        f"  1 回の推薦の時間: {old_summary['seconds']['total']:.1f} 秒 → "
        f"{new_summary['seconds']['total']:.1f} 秒"
    )
    return "\n".join(lines)


def config_document(
    args: argparse.Namespace, settings: Settings, dataset: EvaluationDataset
) -> dict[str, Any]:
    return {
        "profiles": args.profiles,
        "repeats": args.repeat,
        "budget": args.budget,
        "occupations": len(dataset.cases),
        "chat_model": settings.chat_model,
        "selection_model": settings.selection_model,
        "embedding_model": settings.embedding_model,
        "candidate_limit": settings.selection_candidate_limit,
        "prompts": {
            "occupation": _digest(occupation_prompt.INSTRUCTIONS.encode("utf-8")),
            "selection": _digest(selection_prompt.INSTRUCTIONS.encode("utf-8")),
        },
        "dataset": _digest(args.dataset.read_bytes()),
        "judgments": _digest(args.judgments.read_bytes()),
    }


def _run(args: argparse.Namespace) -> None:
    try:
        dataset = load_dataset(args.dataset)
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"評価データを読めません: {args.dataset}: {error!r}")
    try:
        judgments = load_judgments(args.judgments, dataset)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        sys.exit(f"判定を読めません: {args.judgments}: {error!r}")
    settings = load_settings()
    models = [settings.selection_model]
    if args.profiles == "analyzed":
        models.append(settings.chat_model)
    if missing := unpriced(models):
        sys.exit(f"料金表に無いモデルでは費用の上限を守れないので流しません: {'、'.join(missing)}")
    try:
        analyzer = (
            HandwrittenProfiles(dataset)
            if args.profiles == "handwritten"
            else openai_occupation_analyzer(settings)
        )
    except OccupationProfileError as error:
        sys.exit(f"評価データの手書きのスキルを使えません: {error}")
    engine = database_engine(settings)
    meter = LangChainUsageMeter()
    try:
        experiment = RunExperiment(
            search_courses(settings, engine),
            SqlCourseRepository(engine),
            analyzer,
            openai_course_selector(settings),
            settings.selection_candidate_limit,
            meter,
        )
    except EvaluationError as error:
        sys.exit(str(error))
    created = datetime.now(UNIVERSITY_TIME)
    commit = _commit()
    config = config_document(args, settings, dataset)
    path = args.out / f"{created:%Y%m%d-%H%M%S}-{args.label}.json"
    try:
        args.out.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=False)
    except OSError as error:
        sys.exit(f"結果を書く場所を作れません: {error}")
    for stop in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(stop, signal.default_int_handler)
    with meter.meter() as spent:
        try:
            collection = collect(
                experiment.trials(dataset, judgments, args.repeat),
                len(dataset.cases) * args.repeat,
                args.budget,
                spent,
            )
        finally:
            engine.dispose()
    if not collection.outcomes:
        path.unlink()
        sys.exit(f"推薦を 1 回も流せませんでした: {collection.stopped}")
    try:
        summary = summarize(collection.outcomes, dataset.cases)
        document = {
            "label": args.label,
            "created": created.isoformat(timespec="seconds"),
            "commit": commit,
            "stopped": collection.stopped,
            "spent_yen": yen(spent()),
            "config": config,
            "summary": None if summary is None else summary_document(summary),
            "trials": [trial_document(outcome) for outcome in collection.outcomes],
        }
        path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", "utf-8")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    print(render(document))
    print(f"保存した: {path}")
    if collection.stopped is not None and not collection.over_budget:
        sys.exit(1)


def _compare(args: argparse.Namespace) -> None:
    try:
        before, after = (json.loads(path.read_text(encoding="utf-8")) for path in args.runs)
    except (OSError, ValueError) as error:
        sys.exit(f"実験の結果を読めません: {error}")
    unscored = [run["label"] for run in (before, after) if run["summary"] is None]
    if unscored:
        sys.exit(f"集計の無い結果は比べられません: {'、'.join(unscored)}")
    print(compare(before, after))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="推薦を通しで流して、精度・揺れ・費用・時間を測る")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="評価データの職業ごとに推薦を流して結果を JSON に残す")
    run.add_argument("--label", type=label, required=True)
    run.add_argument("--repeat", type=int, default=3)
    run.add_argument("--profiles", choices=PROFILES, default="analyzed")
    run.add_argument("--budget", type=float, default=100)
    run.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    run.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    run.add_argument("--out", type=Path, default=RUNS)
    run.set_defaults(handle=_run)
    versus = commands.add_parser("compare", help="2 つの実験の結果を比べる")
    versus.add_argument("runs", type=Path, nargs=2)
    versus.set_defaults(handle=_compare)
    args = parser.parse_args(argv)
    if args.command == "run" and args.repeat < 1:
        parser.error("--repeat は 1 以上にしてください")
    if args.command == "run" and not (math.isfinite(args.budget) and args.budget > 0):
        parser.error("--budget は 0 より大きい数にしてください")
    args.handle(args)


if __name__ == "__main__":
    main()
