import argparse
import hashlib
import json
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
    Spread,
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
METRICS = (
    *((f"recall@{depth}", f"検索の再現率 @{depth}") for depth in RECALL_DEPTHS),
    ("core_precision", "中心の適合率"),
    ("expected_as_core", "期待する科目を中心に選んだ割合"),
    ("unrelated", "選んだ科目のうち関係なし"),
    ("cores", "1 職業に選んだ中心"),
    ("foundations", "1 職業に選んだ土台"),
)


def yen(usage: Mapping[str, TokenUsage]) -> float:
    total = 0.0
    for model, tokens in usage.items():
        price = next((rates for name, rates in PRICES.items() if model.startswith(name)), None)
        if price is None:
            continue
        fresh, cached, output = price
        total += (
            (tokens.input - tokens.cached) * fresh + tokens.cached * cached + tokens.output * output
        ) / 1_000_000
    return total * YEN_PER_DOLLAR


def unpriced(usage: Mapping[str, TokenUsage]) -> list[str]:
    return sorted(model for model in usage if not any(model.startswith(name) for name in PRICES))


def _digest(text: str | bytes) -> str:
    data = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(data).hexdigest()[:8]


def _commit() -> str | None:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return f"{head}-dirty" if dirty else head


def _spread(value: Spread) -> dict[str, float]:
    return asdict(value)


def summary_document(summary: ExperimentSummary) -> dict[str, Any]:
    plans = summary.trials - summary.failures
    document: dict[str, Any] = {"trials": summary.trials, "failures": summary.failures}
    for depth, value in zip(RECALL_DEPTHS, summary.recall, strict=True):
        document[f"recall@{depth}"] = _spread(value)
    document |= {
        "core_precision": _spread(summary.core_precision),
        "expected_as_core": _spread(summary.expected_as_core),
        "unrelated": _spread(summary.unrelated),
        "cores": _spread(summary.cores),
        "foundations": _spread(summary.foundations),
        "overlap": summary.overlap,
        "core_overlap": summary.core_overlap,
        "yen_per_plan": yen(summary.usage) / plans,
        "tokens_per_plan": {
            model: {
                "input": tokens.input / plans,
                "cached": tokens.cached / plans,
                "output": tokens.output / plans,
            }
            for model, tokens in summary.usage.items()
        },
        "seconds": asdict(summary.seconds) | {"total": summary.seconds.total},
        "unpriced_models": unpriced(summary.usage),
    }
    return document


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


def _percent(value: Mapping[str, float]) -> str:
    return (
        f"{value['mean']:.0%} ± {value['std'] * 100:.0f}({value['low']:.0%}〜{value['high']:.0%})"
    )


def _number(value: Mapping[str, float]) -> str:
    return f"{value['mean']:.2f} ± {value['std']:.2f}({value['low']:.2f}〜{value['high']:.2f})"


def _format(key: str, value: Mapping[str, float]) -> str:
    return (
        _number(value)
        if key.startswith("recall") or key in ("cores", "foundations")
        else _percent(value)
    )


def render(document: Mapping[str, Any]) -> str:
    config, summary = document["config"], document["summary"]
    lines = [
        f"実験 {document['label']}({document['created']}、commit {document['commit']}、"
        f"{config['occupations']} 職業 × {config['repeats']} 回、"
        f"職業の読み取り {config['profiles']}、"
        f"{config['chat_model']} / {config['selection_model']}、候補 {config['candidate_limit']})",
    ]
    if not document["complete"]:
        lines.append(f"  費用の上限 {config['budget']} 円で途中で止めた")
    lines.append(f"  推薦 {summary['trials']} 回、失敗 {summary['failures']} 回")
    lines += [f"  {label} {_format(key, summary[key])}" for key, label in METRICS]
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
    lines.append(f"  1 件あたり {summary['yen_per_plan']:.2f} 円({tokens})")
    lines.append(
        f"  1 件あたりの時間 {seconds['total']:.1f} 秒(読み取り {seconds['reading']:.1f}、"
        f"検索 {seconds['searching']:.1f}、選び直し {seconds['selecting']:.1f})"
    )
    if summary["unpriced_models"]:
        lines.append(f"  料金表に無いモデル: {'、'.join(summary['unpriced_models'])}")
    return "\n".join(lines)


def compare(before: Mapping[str, Any], after: Mapping[str, Any]) -> str:
    lines = [f"比べる: {before['label']} → {after['label']}"]
    for key, label in METRICS:
        old, new = before["summary"][key], after["summary"][key]
        delta = new["mean"] - old["mean"]
        noise = max(old["std"], new["std"])
        repeated = before["config"]["repeats"] > 1 and after["config"]["repeats"] > 1
        verdict = ("揺れより大きい" if abs(delta) > noise else "揺れの範囲") if repeated else "-"
        scale = 1 if key.startswith("recall") or key in ("cores", "foundations") else 100
        unit = "" if scale == 1 else " ポイント"
        lines.append(
            f"  {label}: {_format(key, old)} → {_format(key, new)}、"
            f"差 {delta * scale:+.2f}{unit}、{verdict}"
        )
    for key, label in (
        ("overlap", "揺れ(選んだ科目の重なり)"),
        ("core_overlap", "揺れ(中心の重なり)"),
    ):
        old, new = before["summary"][key], after["summary"][key]
        if old is not None and new is not None:
            lines.append(f"  {label}: {old:.2f} → {new:.2f}、差 {new - old:+.2f}")
    lines.append(
        f"  1 件あたりの費用: {before['summary']['yen_per_plan']:.2f} 円 → "
        f"{after['summary']['yen_per_plan']:.2f} 円"
    )
    lines.append(
        f"  1 件あたりの時間: {before['summary']['seconds']['total']:.1f} 秒 → "
        f"{after['summary']['seconds']['total']:.1f} 秒"
    )
    return "\n".join(lines)


def _run(args: argparse.Namespace) -> None:
    try:
        dataset = load_dataset(args.dataset)
        judgments = load_judgments(args.judgments, dataset)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        sys.exit(f"評価データか判定を読めません: {error!r}")
    settings = load_settings()
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
    outcomes: list[Trial | FailedTrial] = []
    spent = 0.0
    total = len(dataset.cases) * args.repeat
    try:
        for outcome in experiment.trials(dataset, judgments, args.repeat):
            outcomes.append(outcome)
            if isinstance(outcome, Trial):
                spent += yen(outcome.usage)
                detail = f"{yen(outcome.usage):.2f} 円、{outcome.seconds.total:.1f} 秒"
            else:
                detail = f"失敗: {outcome.failure}"
            print(
                f"{len(outcomes)}/{total} {outcome.occupation}({outcome.repeat} 回目){detail}、"
                f"ここまで {spent:.1f} 円",
                file=sys.stderr,
            )
            if spent >= args.budget:
                break
    except (
        EvaluationError,
        SearchError,
        OccupationProfileError,
        RecommendationError,
        EmbeddingError,
    ) as error:
        sys.exit(f"実験を止めました: {error}")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    except OSError as error:
        sys.exit(f"ネットワークに失敗しました: {error}")
    finally:
        engine.dispose()
    try:
        summary = summarize(outcomes, dataset.cases)
    except ValueError as error:
        sys.exit(f"実験を止めました: {error}")
    created = datetime.now(JST)
    document = {
        "label": args.label,
        "created": created.isoformat(timespec="seconds"),
        "commit": _commit(),
        "complete": len(outcomes) == total,
        "config": config_document(
            args,
            settings.chat_model,
            settings.selection_model,
            settings.embedding_model,
            settings.selection_candidate_limit,
            dataset,
        ),
        "summary": summary_document(summary),
        "trials": [trial_document(outcome) for outcome in outcomes],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"{created:%Y%m%d-%H%M}-{args.label}.json"
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(render(document))
    print(f"保存した: {path}")


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
            "occupation": _digest(occupation_prompt.INSTRUCTIONS),
            "selection": _digest(selection_prompt.INSTRUCTIONS),
        },
        "dataset": _digest(args.dataset.read_bytes()),
        "judgments": _digest(args.judgments.read_bytes()),
    }


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
    run.add_argument("--label", required=True)
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
    args.handle(args)


if __name__ == "__main__":
    main()
