import argparse
import json
import math
import re
import signal
import sys
import traceback
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.analyze_experiment import (
    TOP_COURSES,
    TOP_OCCUPATIONS,
    AnalyzeExperiment,
    CourseTally,
    ExperimentAnalysis,
    Fate,
)
from app.application.compare_experiments import (
    CONFIDENCE,
    MIN_OCCUPATIONS,
    RESAMPLES,
    SHUFFLES,
    SIGNIFICANCE,
    TOLERANCE,
    Change,
    Comparison,
    aligned,
    compare_experiments,
)
from app.application.evaluate_search import (
    RECALL_CUTOFFS,
    EvaluationCase,
    EvaluationDataset,
    EvaluationError,
    HandwrittenProfiles,
)
from app.application.evaluate_selection import (
    ExpectedCourse,
    Judgment,
    Judgments,
    Pick,
    SelectionResult,
    UnlinkedPick,
)
from app.application.ports import EmbeddingError, TokenUsage
from app.application.run_experiment import (
    ExperimentSummary,
    FailedTrial,
    RunExperiment,
    Scorecard,
    ScoredRun,
    Side,
    Trial,
    interleave,
    scored_run,
    summarize,
)
from app.application.search_courses import SearchError
from app.domain.course import UNIVERSITY_TIME
from app.domain.recommendation import Relevance
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.llm import openai_occupation_analyzer as occupation_prompt
from app.infrastructure.llm.openai_course_selector import INSTRUCTIONS as SELECTION_INSTRUCTIONS
from app.infrastructure.llm.usage_meter import LangChainUsageMeter
from app.presentation.cli.evaluation_data import (
    DEFAULT_DATASET,
    DEFAULT_JUDGMENTS,
    load_dataset,
    load_judgments,
    shown_reason,
    silence_heldout_logs,
)
from app.presentation.cli.labels import JUDGMENT_LABELS, SEARCH_MODES
from app.presentation.cli.records import (
    YEN_PER_DOLLAR,
    current_commit,
    digest,
    label,
    reserve,
)
from app.presentation.composition import (
    course_selector,
    database_engine,
    load_settings,
    occupation_analyzer,
    search_courses,
)
from app.settings import Settings

RUNS = DEFAULT_DATASET.with_name("runs")
HELDOUT_RUNS = DEFAULT_DATASET.parents[1] / "data" / "heldout-runs"
PRICES = {
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
}
FAILURE_STREAK_LIMIT = 3
STOPPING_ERRORS: tuple[type[Exception], ...] = (EvaluationError, SearchError, SQLAlchemyError)
RUN_CONTROLS = frozenset({"budget"})
GRADING = ("dataset", "judgments")
UNRECORDED_SETTINGS = {
    "selection_votes": 1,
    "selection_vote_delay_seconds": 0.0,
    "occupation_reading_cache_size": 0,
    "search_by_skill": False,
}
PROFILES = ("analyzed", "handwritten")
READING_SETTINGS = ("CHAT_MODEL", "OCCUPATION_READING_CACHE_SIZE")
PROMPT_SETTING = "SELECTION_PROMPT"
PAIRABLE_SETTINGS = (
    *READING_SETTINGS,
    "EMBEDDING_MODEL",
    "SEARCH_BY_SKILL",
    "SELECTION_MODEL",
    "SELECTION_CANDIDATE_LIMIT",
    "SELECTION_VOTES",
    "SELECTION_VOTE_DELAY_SECONDS",
    PROMPT_SETTING,
)
UNEXPANDED = re.compile(r"\{[^{}]*\}|\{\{|\}\}|\\\n")
SIDE_NAMES = {Side.BEFORE: "前", Side.AFTER: "後"}
METRICS = (
    *((f"recall@{cutoff}", f"検索の再現率 @{cutoff}", "ratio") for cutoff in RECALL_CUTOFFS),
    ("candidate_recall", "選び直しに渡した候補の再現率", "ratio"),
    ("core_precision", "中心の適合率", "ratio"),
    ("expected_as_core", "期待する科目を中心に選んだ割合", "ratio"),
    ("unrelated", "選んだ科目のうち関係なし", "ratio"),
    ("cores", "1 職業に選んだ中心", "count"),
    ("foundations", "1 職業に選んだ土台", "count"),
)
OVERLAPS = (
    ("overlap", "揺れ(選んだ科目の重なり)", "coefficient"),
    ("core_overlap", "揺れ(中心の重なり)", "coefficient"),
)
FATE_LABELS = {
    Fate.CORE: "中心に選んだ",
    Fate.FOUNDATION: "土台に選んだ",
    Fate.UNLINKED: "土台に選んだが中心につながらず外した",
    Fate.SKIPPED: "候補にあったが選ばなかった(選び直しで落とした)",
    Fate.READING: "候補に無く、手書きのスキルなら入る(読み取りで落とした)",
    Fate.SEARCH: "候補に無く、手書きのスキルでも入らない(検索で落とした)",
}
STAGE_LABELS = {
    Fate.UNLINKED: "外した",
    Fate.SKIPPED: "選び直し",
    Fate.READING: "読み取り",
    Fate.SEARCH: "検索",
}
PICK_LABELS = {Fate.CORE: "中心", Fate.FOUNDATION: "土台"}
PLACEMENT_LABELS = PICK_LABELS | {Fate.UNLINKED: "外した土台"}


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


def setting(text: str) -> tuple[str, str]:
    name, _, value = text.partition("=")
    if not value or name not in PAIRABLE_SETTINGS:
        raise argparse.ArgumentTypeError(
            f"設定=値 の形で書いてください。替えられるのは {'、'.join(PAIRABLE_SETTINGS)}"
        )
    return name, value


def trial_instructions(path: str | None) -> str:
    if path is None:
        return SELECTION_INSTRUCTIONS
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        sys.exit(f"{PROMPT_SETTING} を読めません: {error}")
    if not text:
        sys.exit(f"{PROMPT_SETTING} の文面が空です: {path}")
    if UNEXPANDED.search(text):
        sys.exit(
            f"{PROMPT_SETTING} に組み込みの文面の書き方(波括弧や行末の \\)が"
            "残っています。展開した文面から作ってください"
        )
    return text


@dataclass(frozen=True)
class Collection:
    outcomes: list[tuple[Side | None, Trial | FailedTrial]]
    stopped: str | None
    over_budget: bool

    def of(self, side: Side | None) -> list[Trial | FailedTrial]:
        return [outcome for taken, outcome in self.outcomes if taken is side]


def stop_reason(error: Exception) -> str:
    if isinstance(error, EvaluationError):
        return f"評価データが合わない: {error}"
    if isinstance(error, OperationalError):
        return f"DB に接続できません: {error.orig}"
    if isinstance(error, SQLAlchemyError):
        return f"DB の操作に失敗しました: {error}"
    return str(error)


def collect(
    outcomes: Iterator[tuple[Side | None, Trial | FailedTrial]],
    total: int,
    budget: float,
    spent: Callable[[], dict[str, TokenUsage]],
    unit: int = 1,
    heldout: bool = False,
) -> Collection:
    collected: list[tuple[Side | None, Trial | FailedTrial]] = []
    streaks: Counter[Side | None] = Counter()
    try:
        for side, outcome in outcomes:
            collected.append((side, outcome))
            streaks[side] = streaks[side] + 1 if isinstance(outcome, FailedTrial) else 0
            usage = spent()
            detail = (
                f"{outcome.seconds.total:.1f} 秒"
                if isinstance(outcome, Trial)
                else f"失敗: {shown_reason(outcome.failure, heldout)}"
            )
            where = "" if side is None else f"{SIDE_NAMES[side]} "
            print(
                f"{len(collected)}/{total} {where}{outcome.occupation}({outcome.repeat} 回目)"
                f"{yen(outcome.usage):.2f} 円、{detail}、ここまで {yen(usage):.1f} 円",
                file=sys.stderr,
            )
            if missing := unpriced(list(usage)):
                return Collection(
                    collected, f"料金表に無いモデルが答えた: {'、'.join(missing)}", False
                )
            if streaks[side] >= FAILURE_STREAK_LIMIT:
                whose = "" if side is None else f"{SIDE_NAMES[side]}の"
                return Collection(
                    collected, f"{whose}推薦が {streaks[side]} 回続けて失敗した", False
                )
            if yen(usage) >= budget and len(collected) < total and len(collected) % unit == 0:
                return Collection(collected, f"費用の上限 {budget:g} 円に達した", True)
    except STOPPING_ERRORS as error:
        return Collection(collected, shown_reason(stop_reason(error), heldout), False)
    except OSError as error:
        return Collection(collected, f"入出力に失敗しました: {shown_reason(error, heldout)}", False)
    except KeyboardInterrupt:
        return Collection(collected, "中断した", False)
    except Exception as error:
        if not heldout:
            traceback.print_exc()
        unexpected = shown_reason(repr(error), heldout)
        return Collection(collected, f"思わぬ失敗で止まった: {unexpected}", False)
    return Collection(collected, None, False)


def summary_document(summary: ExperimentSummary) -> dict[str, Any]:
    return {
        "trials": summary.trials,
        "failures": summary.failures,
        "complete_repeats": summary.complete_repeats,
        "scored_repeats": summary.scored_repeats,
        **{key: None if value is None else asdict(value) for key, value in summary.metrics.items()},
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
    recommendation = outcome.recommendation
    judged = {pick.name: pick.judgment.value for pick in outcome.result.picks} | {
        pick.name: pick.judgment.value for pick in outcome.result.unlinked
    }
    return {
        "occupation": outcome.occupation,
        "repeat": outcome.repeat,
        "interpretation": recommendation.profile.interpretation,
        "assumption": recommendation.profile.assumption,
        "skills": list(recommendation.profile.skills),
        "candidates": list(recommendation.candidates),
        "courses": [
            {
                "name": course.name,
                "relevance": course.relevance.value,
                "judgment": judged[course.name],
                "reason": course.reason,
                "prerequisite_for": course.prerequisite_for,
            }
            for course in recommendation.courses
        ],
        "unlinked": [
            {
                "name": choice.name,
                "judgment": judged[choice.name],
                "reason": choice.reason,
                "prerequisite_for": choice.prerequisite_for,
            }
            for choice in recommendation.unlinked
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


def scorecard(document: Mapping[str, Any]) -> Scorecard:
    occupation = document["occupation"]
    if not document["expected"]:
        raise ValueError(f"{occupation}: 期待する科目がありません")
    return Scorecard(
        occupation,
        document["repeat"],
        tuple(document["candidates"]),
        SelectionResult(
            occupation,
            tuple(
                Pick(course["name"], Relevance(course["relevance"]), Judgment(course["judgment"]))
                for course in document["courses"]
            ),
            tuple(
                ExpectedCourse(
                    course["name"],
                    None if course["picked"] is None else Relevance(course["picked"]),
                    course["searched"],
                    course["unlinked"],
                )
                for course in document["expected"]
            ),
            tuple(
                UnlinkedPick(
                    course["name"], course["prerequisite_for"], Judgment(course["judgment"])
                )
                for course in document["unlinked"]
            ),
        ),
    )


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
    models = " / ".join(
        model for model in (config["chat_model"], config["selection_model"]) if model
    )
    lines = [
        f"実験 {document['label']}({document['created']}、commit {document['commit']}、"
        f"{config['occupations']} 職業 × {config['repeats']} 回、"
        f"職業の読み取り {config['profiles']}、{models}、埋め込み {config['embedding_model']}、"
        f"検索 {SEARCH_MODES[config['search_by_skill']]}、"
        f"候補 {config['candidate_limit']}、"
        f"選び直し {config['selection_votes']} 回、"
        f"2 票目から {config['selection_vote_delay_seconds']:g} 秒遅らせる)",
    ]
    if document["stopped"] is not None:
        lines.append(f"  途中で止めた: {document['stopped']}")
    if pair := document.get("pair"):
        lines.append(
            f"  使った費用 {document['spent_yen']:.1f} 円(この側の推薦の分。交互に流した組 "
            f"{pair['label']} の 2 つで {pair['spent_yen']:.1f} 円、途中で止めた推薦の分を含む)"
        )
    else:
        lines.append(f"  使った費用 {document['spent_yen']:.1f} 円")
    if summary is None:
        lines.append(
            "  推薦が全て失敗したので集計していない"
            if document["trials"]
            else "  この側の推薦を流す前に止まったので集計していない"
        )
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


def _value(kind: str, value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1%}" if kind == "ratio" else f"{value:.2f}"


def _signed(kind: str, value: float) -> str:
    return f"{value * 100:+z.1f}" if kind == "ratio" else f"{value:+z.2f}"


def _change(kind: str, change: Change) -> str:
    values = f"{_value(kind, change.before)} → {_value(kind, change.after)}"
    if change.difference is None:
        return values
    unit = " ポイント" if kind == "ratio" else ""
    difference = f"{values}、差 {_signed(kind, change.difference)}{unit}"
    if change.interval is None and change.p_value is None:
        return f"{difference}、区間と判定なし"
    interval = (
        "区間なし"
        if change.interval is None
        else f"区間 {_signed(kind, change.interval.low)}〜{_signed(kind, change.interval.high)}"
    )
    if change.p_value is None:
        return f"{difference}({interval})、判定なし"
    p_value = (
        "p < 0.001"
        if change.p_value < 0.001
        else f"p = {math.floor(change.p_value * 1000 + TOLERANCE) / 1000:.3f}"
    )
    verdict = "差あり" if change.clear else "はっきりしない"
    return f"{difference}({interval}、{p_value})、{verdict}"


def ran_interleaved(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    pairs = [run.get("pair") or {} for run in (before, after)]
    return (
        {pair.get("side") for pair in pairs} == {"before", "after"}
        and pairs[0].get("label") is not None
        and pairs[0].get("label") == pairs[1].get("label")
        and before.get("created") == after.get("created")
    )


def compare(before: Mapping[str, Any], after: Mapping[str, Any], comparison: Comparison) -> str:
    old_summary, new_summary = before["summary"], after["summary"]
    lines = [f"比べる: {before['label']} → {after['label']}"]
    for run in (before, after):
        stopped = "" if run["stopped"] is None else f"、途中で止めた({run['stopped']})"
        lines.append(f"  {run['label']}: {_counts(run['summary'])}{stopped}")
    old_config = UNRECORDED_SETTINGS | before["config"] | {"commit": before["commit"]}
    new_config = UNRECORDED_SETTINGS | after["config"] | {"commit": after["commit"]}
    differences = [
        f"{key} {old_config.get(key)} → {new_config.get(key)}"
        for key in sorted(old_config.keys() | new_config.keys())
        if key not in RUN_CONTROLS and old_config.get(key) != new_config.get(key)
    ]
    if differences:
        lines.append(f"  設定の違い: {'、'.join(differences)}")
    if any(old_config.get(key) != new_config.get(key) for key in GRADING):
        lines.append("  評価データか判定が違うので、差には正解の付け直しの分も入る")
    if not ran_interleaved(before, after):
        lines.append("  交互に流した組でないので、差に流した時刻の揺れも入る(交互に流すのは pair)")
    if comparison.occupations >= MIN_OCCUPATIONS:
        lines.append(
            f"  両方にそろった {comparison.occupations} 職業で比べる。差ありは職業ごとに前と後を"
            f"入れ替える並べ替え検定({SHUFFLES:,} 通り)で p < {SIGNIFICANCE:g}、区間は "
            f"{CONFIDENCE:.0%} 信頼区間(職業を選び直すブートストラップ {RESAMPLES:,} 回)"
        )
    else:
        lines.append(
            f"  両方にそろった {comparison.occupations} 職業で比べる。{MIN_OCCUPATIONS} 職業に"
            "満たないので区間と判定は出さない"
        )
    old_repeats, new_repeats = comparison.repeats
    measured = [change for change in comparison.changes.values() if change.difference is not None]
    if comparison.occupations >= MIN_OCCUPATIONS:
        if any(change.interval is None for change in measured):
            lines.append("  区間なしの指標は、職業を選び直すと割合を出せない組がある")
        if old_repeats != new_repeats:
            lines.append(
                f"  採点した回の数が違う({old_repeats} 回と {new_repeats} 回)ので、"
                "重なり以外は前と後を入れ替えられず判定なし"
            )
        elif any(change.p_value is None for change in measured):
            lines.append("  判定なしの指標は、前と後を入れ替えると割合を出せない組がある")
    narrowed = (old_repeats, new_repeats) != (
        before["summary"]["scored_repeats"],
        after["summary"]["scored_repeats"],
    )
    if narrowed:
        lines.append(f"  前と後の両方で採点した {old_repeats} 回だけで比べる")
    if narrowed or any(
        run["config"]["occupations"] != comparison.occupations for run in (before, after)
    ):
        sizes = "、".join(
            f"{run['label']} {run['config']['occupations']} 職業 × "
            f"{run['summary']['scored_repeats']} 回"
            for run in (before, after)
        )
        lines.append(f"  前と後の値は、それぞれの集計({sizes})と違うことがある")
    for key, name, kind in (*METRICS, *OVERLAPS):
        lines.append(f"  {name}: {_change(kind, comparison.changes[key])}")
    lines.append(
        f"  1 回の推薦あたりの費用: {old_summary['yen_per_plan']:.2f} 円 → "
        f"{new_summary['yen_per_plan']:.2f} 円"
    )
    lines.append(
        f"  1 回の推薦の時間: {old_summary['seconds']['total']:.1f} 秒 → "
        f"{new_summary['seconds']['total']:.1f} 秒"
    )
    return "\n".join(lines)


def _tally_line(tally: CourseTally, labels: Mapping[Fate, str]) -> str:
    breakdown = "、".join(
        f"{label} {tally.counts[fate]}" for fate, label in labels.items() if fate in tally.counts
    )
    return f"  {tally.name} {tally.total} 回({tally.occupations} 職業): {breakdown}"


def render_analysis(
    heading: Sequence[str],
    readings: Mapping[tuple[str, int], str],
    analysis: ExperimentAnalysis,
    dataset: EvaluationDataset,
) -> str:
    total = sum(analysis.fates.values())
    lines = [
        *heading,
        f"期待する科目の行方({total} 件。期待する科目 × 採点した推薦)",
        *(
            f"  {FATE_LABELS[fate]} {count}({count / total:.1%})"
            for fate, count in analysis.fates.items()
        ),
        "選んだ授業の判定",
        *(
            f"  {PLACEMENT_LABELS[placement]} {sum(counts.values())}: "
            + "、".join(
                f"{JUDGMENT_LABELS[judgment]} {count}" for judgment, count in counts.items()
            )
            for placement, counts in analysis.judgments.items()
        ),
        f"落とした回数の多い期待する科目(上から {TOP_COURSES} 件)",
        *(_tally_line(tally, STAGE_LABELS) for tally in analysis.missed),
        f"関係なしで選んだ回数の多い科目(上から {TOP_COURSES} 件)",
        *(_tally_line(tally, PICK_LABELS) for tally in analysis.unrelated),
        f"読み取りで落とした数の多い職業(上から {TOP_OCCUPATIONS} 件)",
    ]
    skills_of = {case.occupation: case.skills for case in dataset.cases}
    for loss in analysis.reading_losses:
        repeats_of: dict[str, list[int]] = defaultdict(list)
        for repeat in loss.repeats:
            repeats_of[readings[loss.occupation, repeat]].append(repeat)
        courses = "、".join(f"{name} {count}" for name, count in loss.courses.items())
        lines += [
            f"  {loss.occupation} {loss.total} 件: {courses}",
            *(
                f"    {'、'.join(map(str, repeats))} 回目の読み取り: {reading}"
                for reading, repeats in repeats_of.items()
            ),
            f"    手書きのスキル: {' / '.join(skills_of[loss.occupation])}",
        ]
    return "\n".join(lines)


def search_config(settings: Settings) -> dict[str, Any]:
    return {
        "embedding_model": settings.embedding_model,
        "search_by_skill": settings.search_by_skill,
        "candidate_limit": settings.selection_candidate_limit,
    }


def scored(document: Mapping[str, Any]) -> ScoredRun:
    return scored_run(
        [scorecard(trial) for trial in document["trials"] if "failure" not in trial],
        document["config"]["occupations"],
    )


def config_document(
    args: argparse.Namespace,
    settings: Settings,
    dataset: EvaluationDataset,
    instructions: str,
) -> dict[str, Any]:
    analyzed = args.profiles == "analyzed"
    return {
        "profiles": args.profiles,
        "repeats": args.repeat,
        "budget": args.budget,
        "occupations": len(dataset.cases),
        "chat_model": settings.chat_model if analyzed else None,
        "occupation_reading_cache_size": settings.occupation_reading_cache_size if analyzed else 0,
        "selection_model": settings.selection_model,
        "selection_votes": settings.selection_votes,
        "selection_vote_delay_seconds": settings.selection_vote_delay_seconds,
        **search_config(settings),
        "prompts": {
            "occupation": (
                digest(occupation_prompt.INSTRUCTIONS.encode("utf-8")) if analyzed else None
            ),
            "selection": digest(instructions.encode("utf-8")),
        },
        "dataset": digest(args.dataset.read_bytes()),
        "judgments": digest(args.judgments.read_bytes()),
    }


def _inputs(args: argparse.Namespace) -> tuple[EvaluationDataset, Judgments]:
    try:
        dataset = load_dataset(args.dataset)
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"評価データを読めません: {args.dataset}: {error!r}")
    try:
        judgments = load_judgments(args.judgments, dataset)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        sys.exit(f"判定を読めません: {args.judgments}: {error!r}")
    return dataset, judgments


def _experiment(
    args: argparse.Namespace,
    settings: Settings,
    dataset: EvaluationDataset,
    engine: Engine,
    meter: LangChainUsageMeter,
    instructions: str,
) -> RunExperiment:
    models = [settings.selection_model]
    if args.profiles == "analyzed":
        models.append(settings.chat_model)
    if missing := unpriced(models):
        sys.exit(f"料金表に無いモデルでは費用の上限を守れないので流しません: {'、'.join(missing)}")
    analyzer = (
        HandwrittenProfiles(dataset)
        if args.profiles == "handwritten"
        else occupation_analyzer(settings)
    )
    try:
        return RunExperiment(
            search_courses(settings, engine),
            SqlCourseRepository(engine),
            analyzer,
            course_selector(settings, instructions),
            settings.selection_candidate_limit,
            meter,
        )
    except EvaluationError as error:
        sys.exit(str(error))


def _trials(
    experiment: RunExperiment, dataset: EvaluationDataset, judgments: Judgments, repeats: int
) -> Iterator[Trial | FailedTrial]:
    try:
        return experiment.trials(dataset, judgments, repeats)
    except STOPPING_ERRORS as error:
        sys.exit(f"推薦を流せません: {shown_reason(stop_reason(error), dataset.heldout)}")


def results_directory(out: Path | None, dataset: EvaluationDataset) -> Path:
    if not dataset.heldout:
        return RUNS if out is None else out
    if out is not None:
        sys.exit(f"確かめ用の結果は {HELDOUT_RUNS} にだけ書く(--out は受け付けない。ADR 0067)")
    return HELDOUT_RUNS


def _collected(
    outcomes: Iterator[tuple[Side | None, Trial | FailedTrial]],
    total: int,
    budget: float,
    unit: int,
    meter: LangChainUsageMeter,
    engine: Engine,
    heldout: bool,
) -> tuple[Collection, float]:
    for stop in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(stop, signal.default_int_handler)
    with meter.meter() as spent:
        try:
            collection = collect(outcomes, total, budget, spent, unit, heldout)
        finally:
            engine.dispose()
    return collection, yen(spent())


def run_document(
    label: str,
    created: datetime,
    commit: str | None,
    stopped: str | None,
    spent_yen: float,
    config: dict[str, Any],
    outcomes: Sequence[Trial | FailedTrial],
    cases: Sequence[EvaluationCase],
) -> dict[str, Any]:
    summary = summarize(outcomes, cases)
    return {
        "label": label,
        "created": created.isoformat(timespec="seconds"),
        "commit": commit,
        "stopped": stopped,
        "spent_yen": spent_yen,
        "config": config,
        "summary": None if summary is None else summary_document(summary),
        "trials": [trial_document(outcome) for outcome in outcomes],
    }


def pair_documents(
    label: str,
    created: datetime,
    commit: str | None,
    collection: Collection,
    spent_yen: float,
    configs: Mapping[Side, dict[str, Any]],
    names: Mapping[Side, str],
    cases: Sequence[EvaluationCase],
) -> dict[Side, dict[str, Any]]:
    documents: dict[Side, dict[str, Any]] = {}
    for side, partner in ((Side.BEFORE, Side.AFTER), (Side.AFTER, Side.BEFORE)):
        outcomes = collection.of(side)
        documents[side] = run_document(
            f"{label}-{side.value}",
            created,
            commit,
            collection.stopped,
            sum(yen(outcome.usage) for outcome in outcomes),
            configs[side],
            outcomes,
            cases,
        ) | {
            "pair": {
                "label": label,
                "side": side.value,
                "partner": names[partner],
                "spent_yen": spent_yen,
            }
        }
    return documents


def _write(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", "utf-8")


def _run(args: argparse.Namespace) -> None:
    dataset, judgments = _inputs(args)
    out = results_directory(args.out, dataset)
    silence_heldout_logs(dataset)
    settings = load_settings()
    engine = database_engine(settings)
    meter = LangChainUsageMeter()
    experiment = _experiment(args, settings, dataset, engine, meter, SELECTION_INSTRUCTIONS)
    trials = _trials(experiment, dataset, judgments, args.repeat)
    created = datetime.now(UNIVERSITY_TIME)
    commit = current_commit()
    config = config_document(args, settings, dataset, SELECTION_INSTRUCTIONS)
    path = out / f"{created:%Y%m%d-%H%M%S}-{args.label}.json"
    reserve(out, [path])
    collection, spent_yen = _collected(
        ((None, outcome) for outcome in trials),
        len(dataset.cases) * args.repeat,
        args.budget,
        1,
        meter,
        engine,
        dataset.heldout,
    )
    outcomes = collection.of(None)
    if not outcomes:
        path.unlink()
        sys.exit(f"推薦を 1 回も流せませんでした: {collection.stopped}")
    try:
        document = run_document(
            args.label,
            created,
            commit,
            collection.stopped,
            spent_yen,
            config,
            outcomes,
            dataset.cases,
        )
        _write(path, document)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    print(render(document))
    print(f"保存した: {path}")
    if collection.stopped is not None and not collection.over_budget:
        sys.exit(1)


def _pair(args: argparse.Namespace) -> None:
    dataset, judgments = _inputs(args)
    out = results_directory(args.out, dataset)
    silence_heldout_logs(dataset)
    overrides = {Side.BEFORE: args.before, Side.AFTER: args.after}
    instructions = {
        side: trial_instructions(dict(overrides[side]).get(PROMPT_SETTING)) for side in Side
    }
    settings = {
        side: load_settings(
            **{name.lower(): value for name, value in overrides[side] if name != PROMPT_SETTING}
        )
        for side in Side
    }
    engine = database_engine(settings[Side.BEFORE])
    meter = LangChainUsageMeter()
    experiments = {
        side: _experiment(args, settings[side], dataset, engine, meter, instructions[side])
        for side in Side
    }
    trials = {side: _trials(experiments[side], dataset, judgments, args.repeat) for side in Side}
    created = datetime.now(UNIVERSITY_TIME)
    commit = current_commit()
    paths = {side: out / f"{created:%Y%m%d-%H%M%S}-{args.label}-{side.value}.json" for side in Side}
    reserve(out, list(paths.values()))
    collection, spent_yen = _collected(
        interleave(trials[Side.BEFORE], trials[Side.AFTER], len(dataset.cases)),
        len(Side) * len(dataset.cases) * args.repeat,
        args.budget,
        len(Side),
        meter,
        engine,
        dataset.heldout,
    )
    if not collection.outcomes:
        for path in paths.values():
            path.unlink()
        sys.exit(f"推薦を 1 回も流せませんでした: {collection.stopped}")
    try:
        documents = pair_documents(
            args.label,
            created,
            commit,
            collection,
            spent_yen,
            {
                side: config_document(args, settings[side], dataset, instructions[side])
                for side in Side
            },
            {side: path.name for side, path in paths.items()},
            dataset.cases,
        )
        for side, document in documents.items():
            _write(paths[side], document)
    except BaseException:
        for path in paths.values():
            path.unlink(missing_ok=True)
        raise
    for side in Side:
        print(render(documents[side]))
        print(f"保存した: {paths[side]}")
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
    try:
        old_run, new_run = (scored(run) for run in (before, after))
    except (KeyError, TypeError, ValueError) as error:
        sys.exit(f"実験の結果の推薦を読めません: {error!r}")
    if ran_interleaved(before, after):
        old_run, new_run = aligned(old_run, new_run)
        if not old_run.repeats:
            sys.exit("交互に流した組の前と後の両方で採点した回が無いので比べられません")
    print(compare(before, after, compare_experiments(old_run, new_run)))


def _analyze(args: argparse.Namespace) -> None:
    try:
        document = json.loads(args.run.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        sys.exit(f"実験の結果を読めません: {error}")
    try:
        dataset = load_dataset(args.dataset)
        fingerprint = digest(args.dataset.read_bytes())
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"評価データを読めません: {args.dataset}: {error!r}")
    if dataset.heldout:
        sys.exit("確かめ用の評価データは、職業と科目ごとの結果を出すことになるので分析しません")
    try:
        config = UNRECORDED_SETTINGS | document["config"]
        if document["summary"] is None:
            sys.exit(f"集計の無い結果は分析できません: {document['label']}")
        if config["profiles"] != "analyzed":
            sys.exit("手書きのスキルで流した結果は、読み取りを通っていないので分析しません")
        if config["dataset"] != fingerprint:
            sys.exit(
                f"結果は別の評価データで流しています(結果の指紋 {config['dataset']}、"
                f"{args.dataset} の指紋 {fingerprint})"
            )
        run = scored(document)
        readings = {
            (trial["occupation"], trial["repeat"]): trial["interpretation"]
            + ("" if trial["assumption"] is None else f"(前提: {trial['assumption']})")
            + f" / スキル: {' / '.join(trial['skills'])}"
            for trial in document["trials"]
            if "failure" not in trial
        }
        title = (
            f"実験 {document['label']} の分析({document['created']}、commit {document['commit']})"
        )
    except (KeyError, TypeError, ValueError) as error:
        sys.exit(f"実験の結果を読めません: {error!r}")
    settings = load_settings()
    current = search_config(settings)
    differing = [
        f"{key} が結果は {config.get(key)}、今は {value}"
        for key, value in current.items()
        if config.get(key) != value
    ]
    if differing:
        sys.exit(f"結果と同じ取り方で手書きのスキルの検索をできません: {'、'.join(differing)}")
    heading = [
        title,
        f"  採点した推薦 {len(run.cards)} 回(全職業がそろった回 {run.complete_repeats}、"
        f"採点した回 {len(run.repeats)})。手書きのスキルの検索は今の DB で行う"
        f"(埋め込み {current['embedding_model']}、検索 {SEARCH_MODES[current['search_by_skill']]}、"
        f"候補 {current['candidate_limit']})",
    ]
    engine = database_engine(settings)
    try:
        analysis = AnalyzeExperiment(
            search_courses(settings, engine), settings.selection_candidate_limit
        ).run(dataset, run.cards)
    except (EvaluationError, SearchError, EmbeddingError) as error:
        sys.exit(f"分析できません: {error}")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    except OSError as error:
        sys.exit(f"ネットワークかファイルの読み書きに失敗しました: {error}")
    finally:
        engine.dispose()
    print(render_analysis(heading, readings, analysis, dataset))


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="推薦を通しで流して、精度・揺れ・費用・時間を測る")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="評価データの職業ごとに推薦を流して結果を JSON に残す")
    run.add_argument("--label", type=label, required=True)
    run.add_argument("--repeat", type=int, default=3)
    run.add_argument("--profiles", choices=PROFILES, default="analyzed")
    run.add_argument("--budget", type=float, default=100)
    run.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    run.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    run.add_argument("--out", type=Path)
    run.set_defaults(handle=_run)
    pair = commands.add_parser(
        "pair", help="2 つの設定を職業と回の組ごとに交互に流して結果を JSON に 1 つずつ残す"
    )
    pair.add_argument("--label", type=label, required=True)
    for side in ("--before", "--after"):
        pair.add_argument(
            side, type=setting, nargs="+", action="extend", default=[], metavar="設定=値"
        )
    pair.add_argument("--repeat", type=int, default=3)
    pair.add_argument("--profiles", choices=PROFILES, default="analyzed")
    pair.add_argument("--budget", type=float, default=200)
    pair.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    pair.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    pair.add_argument("--out", type=Path)
    pair.set_defaults(handle=_pair)
    versus = commands.add_parser("compare", help="2 つの実験の結果を比べる")
    versus.add_argument("runs", type=Path, nargs=2)
    versus.set_defaults(handle=_compare)
    examine = commands.add_parser(
        "analyze",
        help="実験の結果から、期待する科目をどの段で落としたかと、誤って選んだ科目を数える",
    )
    examine.add_argument("run", type=Path)
    examine.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    examine.set_defaults(handle=_analyze)
    args = parser.parse_args(argv)
    if args.command in ("run", "pair") and args.repeat < 1:
        parser.error("--repeat は 1 以上にしてください")
    if args.command in ("run", "pair") and not (math.isfinite(args.budget) and args.budget > 0):
        parser.error("--budget は 0 より大きい数にしてください")
    if args.command == "pair" and any(
        len({name for name, _ in overrides}) != len(overrides)
        for overrides in (args.before, args.after)
    ):
        parser.error("--before と --after のそれぞれで、同じ設定は 1 回だけ書いてください")
    if (
        args.command == "pair"
        and args.profiles == "handwritten"
        and any(name in READING_SETTINGS for name, _ in (*args.before, *args.after))
    ):
        parser.error(
            "--profiles handwritten では職業の読み取りを使わないので、"
            f"{' と '.join(READING_SETTINGS)} は替えられません"
        )
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = arguments(argv)
    args.handle(args)


if __name__ == "__main__":
    main()
