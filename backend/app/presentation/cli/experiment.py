import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.evaluate_search import EvaluationDataset, EvaluationError
from app.application.evaluate_selection import HandwrittenProfiles
from app.application.ports import EmbeddingError, TokenUsage
from app.application.run_experiment import (
    RECALL_DEPTHS,
    ExperimentSummary,
    FailedTrial,
    RunExperiment,
    Trial,
    summarize,
)
from app.application.search_courses import SearchCourses, SearchError
from app.domain.occupation import OccupationProfileError
from app.domain.recommendation import RecommendationError
from app.infrastructure.db.chunks import SqlChunkRepository
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
    openai_embedder,
    openai_occupation_analyzer,
)

RUNS = DEFAULT_DATASET.with_name("runs")
PRICES = {
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
}
YEN_PER_DOLLAR = 150
JST = ZoneInfo("Asia/Tokyo")
PROFILES = ("analyzed", "handwritten")
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
METRICS = (
    *((f"recall@{depth}", f"検索の再現率 @{depth}", "ratio") for depth in RECALL_DEPTHS),
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
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        changed = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return f"{head}-dirty" if changed else head


def summary_document(summary: ExperimentSummary) -> dict[str, Any]:
    plans = summary.trials - summary.failures
    spreads = dict(
        zip(
            (key for key, _, _ in METRICS),
            (
                *summary.recall,
                summary.core_precision,
                summary.expected_as_core,
                summary.unrelated,
                summary.cores,
                summary.foundations,
            ),
            strict=True,
        )
    )
    return {
        "trials": summary.trials,
        "failures": summary.failures,
        "complete_repeats": summary.complete_repeats,
        **{key: asdict(value) for key, value in spreads.items()},
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
        "seconds": asdict(summary.seconds) | {"total": summary.seconds.total, "plans": plans},
        "unpriced_models": unpriced(list(summary.usage)),
    }


def trial_document(outcome: Trial | FailedTrial) -> dict[str, Any]:
    if isinstance(outcome, FailedTrial):
        return asdict(outcome)
    judged = {pick.name: pick.judgment.value for pick in outcome.result.picks}
    return {
        "occupation": outcome.occupation,
        "repeat": outcome.repeat,
        "skills": list(outcome.skills),
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


def _format(kind: str, value: Mapping[str, float]) -> str:
    if kind == "ratio":
        return (
            f"{value['mean']:.0%} ± {value['std'] * 100:.0f}"
            f"({value['low']:.0%}〜{value['high']:.0%})"
        )
    return f"{value['mean']:.2f} ± {value['std']:.2f}({value['low']:.2f}〜{value['high']:.2f})"


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
    lines.append(
        f"  推薦 {summary['trials']} 回、失敗 {summary['failures']} 回、"
        f"全職業がそろった回 {summary['complete_repeats']}"
    )
    lines += [f"  {name} {_format(kind, summary[key])}" for key, name, kind in METRICS]
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
    if summary["unpriced_models"]:
        lines.append(f"  料金表に無いモデル: {'、'.join(summary['unpriced_models'])}")
    return "\n".join(lines)


def compare(before: Mapping[str, Any], after: Mapping[str, Any]) -> str:
    lines = [f"比べる: {before['label']} → {after['label']}"]
    repeated = before["config"]["repeats"] > 1 and after["config"]["repeats"] > 1
    for key, name, kind in METRICS:
        old, new = before["summary"][key], after["summary"][key]
        delta = new["mean"] - old["mean"]
        noise = max(old["std"], new["std"])
        verdict = ("揺れより大きい" if abs(delta) > noise else "揺れの範囲") if repeated else "-"
        difference = f"{delta * 100:+.0f} ポイント" if kind == "ratio" else f"{delta:+.2f}"
        lines.append(
            f"  {name}: {_format(kind, old)} → {_format(kind, new)}、差 {difference}、{verdict}"
        )
    for key, name in (
        ("overlap", "揺れ(選んだ科目の重なり)"),
        ("core_overlap", "揺れ(中心の重なり)"),
    ):
        old, new = before["summary"][key], after["summary"][key]
        if old is not None and new is not None:
            lines.append(f"  {name}: {old:.2f} → {new:.2f}、差 {new - old:+.2f}")
    lines.append(
        f"  1 回の推薦あたりの費用: {before['summary']['yen_per_plan']:.2f} 円 → "
        f"{after['summary']['yen_per_plan']:.2f} 円"
    )
    lines.append(
        f"  1 回の推薦の時間: {before['summary']['seconds']['total']:.1f} 秒 → "
        f"{after['summary']['seconds']['total']:.1f} 秒"
    )
    return "\n".join(lines)


def config_document(
    args: argparse.Namespace,
    chat_model: str,
    selection_model: str,
    embedding_model: str,
    candidate_limit: int,
    dataset: EvaluationDataset,
) -> dict[str, Any]:
    return {
        "profiles": args.profiles,
        "repeats": args.repeat,
        "budget": args.budget,
        "occupations": len(dataset.cases),
        "chat_model": chat_model,
        "selection_model": selection_model,
        "embedding_model": embedding_model,
        "candidate_limit": candidate_limit,
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
        judgments = load_judgments(args.judgments, dataset)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        sys.exit(f"評価データか判定を読めません: {error!r}")
    settings = load_settings()
    models = [settings.selection_model]
    if args.profiles == "analyzed":
        models.append(settings.chat_model)
    if missing := unpriced(models):
        sys.exit(f"料金表に無いモデルでは費用の上限を守れないので流しません: {'、'.join(missing)}")
    engine = database_engine(settings)
    courses = SqlCourseRepository(engine)
    search = SearchCourses(courses, SqlChunkRepository(engine), openai_embedder(settings))
    analyzer = (
        HandwrittenProfiles(dataset)
        if args.profiles == "handwritten"
        else openai_occupation_analyzer(settings)
    )
    experiment = RunExperiment(
        search,
        courses,
        analyzer,
        openai_course_selector(settings),
        settings.selection_candidate_limit,
        LangChainUsageMeter(),
    )
    created = datetime.now(JST)
    try:
        args.out.mkdir(parents=True, exist_ok=True)
        output = (args.out / f"{created:%Y%m%d-%H%M%S}-{args.label}.json").open(
            "x", encoding="utf-8"
        )
    except OSError as error:
        sys.exit(f"結果を書く場所を作れません: {error}")
    outcomes: list[Trial | FailedTrial] = []
    spent = 0.0
    stopped: str | None = None
    over_budget = False
    total = len(dataset.cases) * args.repeat
    try:
        for outcome in experiment.trials(dataset, judgments, args.repeat):
            outcomes.append(outcome)
            spent += yen(outcome.usage)
            detail = (
                f"{outcome.seconds.total:.1f} 秒"
                if isinstance(outcome, Trial)
                else f"失敗: {outcome.failure}"
            )
            print(
                f"{len(outcomes)}/{total} {outcome.occupation}({outcome.repeat} 回目)"
                f"{yen(outcome.usage):.2f} 円、{detail}、ここまで {spent:.1f} 円",
                file=sys.stderr,
            )
            if missing := unpriced(list(outcome.usage)):
                stopped = f"料金表に無いモデルが答えた: {'、'.join(missing)}"
                break
            if spent >= args.budget and len(outcomes) < total:
                stopped = f"費用の上限 {args.budget:g} 円に達した"
                over_budget = True
                break
    except EvaluationError as error:
        stopped = f"評価データが合わない: {error}"
    except (SearchError, OccupationProfileError, RecommendationError, EmbeddingError) as error:
        stopped = str(error)
    except OperationalError as error:
        stopped = f"DB に接続できません: {error.orig}"
    except SQLAlchemyError as error:
        stopped = f"DB の操作に失敗しました: {error}"
    except OSError as error:
        stopped = f"ネットワークに失敗しました: {error}"
    except KeyboardInterrupt:
        stopped = "中断した"
    finally:
        engine.dispose()
    if not any(isinstance(outcome, Trial) for outcome in outcomes):
        output.close()
        Path(output.name).unlink()
        sys.exit(
            f"集計できる推薦がありません。{stopped or '全ての推薦が失敗しました'}"
            f"(使った費用 {spent:.1f} 円)"
        )
    document = {
        "label": args.label,
        "created": created.isoformat(timespec="seconds"),
        "commit": _commit(),
        "stopped": stopped,
        "config": config_document(
            args,
            settings.chat_model,
            settings.selection_model,
            settings.embedding_model,
            settings.selection_candidate_limit,
            dataset,
        ),
        "summary": summary_document(summarize(outcomes, dataset.cases)),
        "trials": [trial_document(outcome) for outcome in outcomes],
    }
    with output:
        output.write(json.dumps(document, ensure_ascii=False, indent=1) + "\n")
    print(render(document))
    print(f"保存した: {output.name}")
    if stopped is not None and not over_budget:
        sys.exit(1)


def _compare(args: argparse.Namespace) -> None:
    try:
        before, after = (json.loads(path.read_text(encoding="utf-8")) for path in args.runs)
    except (OSError, ValueError) as error:
        sys.exit(f"実験の結果を読めません: {error}")
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
    if args.command == "run" and args.budget <= 0:
        parser.error("--budget は 0 より大きくしてください")
    args.handle(args)


if __name__ == "__main__":
    main()
