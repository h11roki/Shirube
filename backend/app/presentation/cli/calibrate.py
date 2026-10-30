import argparse
import json
import math
import signal
import sys
import traceback
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.evaluate_search import EvaluationDataset, EvaluationError
from app.application.evaluate_selection import Judgments
from app.application.judging import JudgingError
from app.application.measure_calibration import (
    Choices,
    Layout,
    MeasureCalibration,
    OccupationOdds,
    SelectorTrial,
    Target,
    calibration,
    matched,
)
from app.application.ports import ClassificationError, CourseOdds
from app.domain.course import UNIVERSITY_TIME
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import Relevance
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.llm.jev_course_classifier import (
    CRITERIA,
    QUESTION,
    JevCourseClassifier,
)
from app.presentation.cli.evaluation_data import (
    DEFAULT_DATASET,
    DEFAULT_JUDGMENTS,
    load_dataset,
    load_judgments,
)
from app.presentation.cli.records import YEN_PER_DOLLAR, current_commit, digest, label
from app.presentation.composition import database_engine, load_settings

RESULTS = DEFAULT_DATASET.with_name("calibration")
JEV_DOLLARS_PER_MILLION = 0.042
LAYOUTS = {
    "both": (Layout.GROUPED, Layout.SEPARATE),
    "grouped": (Layout.GROUPED,),
    "separate": (Layout.SEPARATE,),
}
LAYOUT_NAMES = {
    Layout.GROUPED: "1 職業 1 回(候補 20 科目をまとめる)",
    Layout.SEPARATE: "1 科目 1 回",
}
TARGET_NAMES = {Target.CORE: "中心", Target.RELEVANT: "関係あり(中心と土台の和)"}


@dataclass(frozen=True)
class Collected:
    measured: dict[Layout, list[OccupationOdds]]
    spent_yen: float
    stopped: str | None
    over_budget: bool


def yen(input_tokens: int) -> float:
    return input_tokens / 1_000_000 * JEV_DOLLARS_PER_MILLION * YEN_PER_DOLLAR


def selector_trials(trials: Iterable[Mapping[str, Any]]) -> list[SelectorTrial]:
    return [
        SelectorTrial(
            trial["occupation"],
            OccupationProfile(
                trial["occupation"],
                trial["interpretation"],
                trial["assumption"],
                tuple(trial["skills"]),
            ),
            tuple(trial["candidates"]),
            tuple((course["name"], Relevance(course["relevance"])) for course in trial["courses"]),
        )
        for trial in trials
    ]


def _grading(dataset_path: Path, judgments_path: Path) -> tuple[EvaluationDataset, Judgments]:
    try:
        dataset = load_dataset(dataset_path)
        judgments = load_judgments(judgments_path, dataset)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        sys.exit(f"評価データか判定を読めません: {error!r}")
    if dataset.heldout:
        sys.exit("確かめ用の評価データでは測りません(ADR 0067、0074)")
    return dataset, judgments


def _require_same_grading(recorded: Mapping[str, Any], dataset: Path, judgments: Path) -> None:
    for key, path in (("dataset", dataset), ("judgments", judgments)):
        if recorded[key] != digest(path.read_bytes()):
            sys.exit(f"結果と違う {path} です(結果の指紋 {recorded[key]})")


def collect(
    measure: MeasureCalibration,
    dataset: EvaluationDataset,
    trials: Sequence[SelectorTrial],
    layouts: Sequence[Layout],
    budget: float,
) -> Collected:
    measured: dict[Layout, list[OccupationOdds]] = {layout: [] for layout in layouts}
    total = len(trials) * len(layouts)
    done = 0

    def stopped(reason: str | None, over_budget: bool = False) -> Collected:
        return Collected(measured, yen(measure.spent_tokens), reason, over_budget)

    try:
        for layout in layouts:
            for occupation in measure.odds(dataset.year, dataset.department, trials, layout):
                measured[layout].append(occupation)
                done += 1
                spent = yen(measure.spent_tokens)
                print(
                    f"{done}/{total} {LAYOUT_NAMES[layout]} {occupation.occupation}: "
                    f"入力 {occupation.input_tokens:,} トークン、計 {spent:.2f} 円",
                    file=sys.stderr,
                )
                if spent >= budget and done < total:
                    return stopped(f"費用の上限 {budget:g} 円に達した", over_budget=True)
    except (EvaluationError, JudgingError, SQLAlchemyError):
        raise
    except ClassificationError as error:
        return stopped(str(error))
    except OSError as error:
        return stopped(f"入出力に失敗しました: {error}")
    except KeyboardInterrupt:
        return stopped("中断した")
    except Exception as error:
        traceback.print_exc()
        return stopped(f"思わぬ失敗で止まった: {error!r}")
    return stopped(None)


def _ratio(part: int, whole: int) -> str:
    return f"{part / whole:.1%}" if whole else "-"


def _choices_lines(selector: Choices, classifier: Choices) -> list[str]:
    return [
        f"    選んだ {selector.picked} 科目のうち関係なし: 選び手 "
        f"{_ratio(selector.unrelated, selector.picked)}、Jev "
        f"{_ratio(classifier.unrelated, classifier.picked)}",
        f"    候補にある期待する科目 {selector.expected} のうち選んだ割合: 選び手 "
        f"{_ratio(selector.expected_picked, selector.expected)}、Jev "
        f"{_ratio(classifier.expected_picked, classifier.expected)}",
        f"    中心 {selector.cores} 科目の適合率: 選び手 "
        f"{_ratio(selector.expected_cores, selector.cores)}、Jev "
        f"{_ratio(classifier.expected_cores, classifier.cores)}",
    ]


def render(
    document: Mapping[str, Any],
    trials: Sequence[SelectorTrial],
    measured: Mapping[Layout, Sequence[OccupationOdds]],
    judgments: Judgments,
) -> str:
    source = document["source"]
    lines = [
        f"Jev の校正 {document['label']}({document['created']}、モデル {document['model']}、"
        f"問いの指紋 {document['prompt']}、元の結果 {source['label']} の "
        f"{document['repeat']} 回目、{len(trials)} 職業)",
        f"  使った費用 {document['spent_yen']:.2f} 円。今の推薦は 1 件 "
        f"{source['yen_per_plan']:.2f} 円(読み取りと選び直しの全て)",
    ]
    if document["stopped"] is not None:
        lines.append(f"  途中で止めた: {document['stopped']}")
    for layout, occupations in measured.items():
        if not occupations:
            continue
        tokens = sum(occupation.input_tokens for occupation in occupations)
        courses = sum(len(occupation.odds) for occupation in occupations)
        lines.append(
            f"{LAYOUT_NAMES[layout]}: {len(occupations)} 職業、{courses} 科目、"
            f"入力 {tokens:,} トークン、{yen(tokens):.2f} 円"
            f"(1 職業 {yen(tokens) / len(occupations):.3f} 円)"
        )
        for target in Target:
            measured_target = calibration(occupations, judgments, target)
            lines.append(
                f"  {TARGET_NAMES[target]}: ECE {measured_target.ece:.3f}、"
                f"Brier {measured_target.brier:.3f}({measured_target.count} 科目)"
            )
            lines += [
                f"    確率 {part.low:.1f}〜{part.high:.1f}: {part.count} 科目、"
                f"平均 {part.mean_probability:.2f}、当たり {part.hit_rate:.0%}"
                for part in measured_target.bins
            ]
        compared = matched(trials, occupations, judgments)
        lines.append(f"  今の選び手と同じ数を選ぶ({compared.occupations} 職業)")
        lines += _choices_lines(compared.selector, compared.classifier)
    return "\n".join(lines)


def _run(args: argparse.Namespace) -> None:
    try:
        source = json.loads(args.run.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        sys.exit(f"実験の結果を読めません: {error}")
    dataset, judgments = _grading(args.dataset, args.judgments)
    try:
        config = source["config"]
        if config["profiles"] != "analyzed" or source["summary"] is None:
            sys.exit("読み取りを通って採点した実験の結果だけを使います")
        _require_same_grading(config, args.dataset, args.judgments)
        origin = {
            "file": args.run.name,
            "label": source["label"],
            "yen_per_plan": source["summary"]["yen_per_plan"],
        }
        trials = selector_trials(
            trial
            for trial in source["trials"]
            if "failure" not in trial and trial["repeat"] == args.repeat
        )
    except (KeyError, TypeError, ValueError) as error:
        sys.exit(f"実験の結果を読めません: {error!r}")
    if not trials:
        sys.exit(f"{args.repeat} 回目の推薦がありません")
    settings = load_settings()
    if settings.jev_api_key is None:
        sys.exit("JEV_API_KEY を .envrc に書いてください")
    created = datetime.now(UNIVERSITY_TIME)
    path = RESULTS / f"{created:%Y%m%d-%H%M%S}-{args.label}.json"
    engine = database_engine(settings)
    classifier = JevCourseClassifier.connect(settings.jev_api_key, settings.jev_model)
    measure = MeasureCalibration(SqlCourseRepository(engine), classifier)
    for stop in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(stop, signal.default_int_handler)
    try:
        collected = collect(measure, dataset, trials, LAYOUTS[args.layout], args.budget)
    except (EvaluationError, JudgingError) as error:
        sys.exit(f"測れません: {error}")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    finally:
        classifier.close()
        engine.dispose()
    document = {
        "label": args.label,
        "created": created.isoformat(timespec="seconds"),
        "commit": current_commit(),
        "model": settings.jev_model,
        "prompt": digest(
            json.dumps({"question": QUESTION, "criteria": CRITERIA}, ensure_ascii=False).encode()
        ),
        "source": origin,
        "repeat": args.repeat,
        "dataset": config["dataset"],
        "judgments": config["judgments"],
        "budget": args.budget,
        "spent_yen": collected.spent_yen,
        "stopped": collected.stopped,
        "trials": [
            {
                "occupation": trial.occupation,
                "interpretation": trial.profile.interpretation,
                "assumption": trial.profile.assumption,
                "skills": list(trial.profile.skills),
                "candidates": list(trial.candidates),
                "courses": [
                    {"name": name, "relevance": relevance.value} for name, relevance in trial.picks
                ],
            }
            for trial in trials
        ],
        "layouts": {
            layout.value: [
                {
                    "occupation": occupation.occupation,
                    "input_tokens": occupation.input_tokens,
                    "odds": [asdict(odds) for odds in occupation.odds],
                }
                for occupation in occupations
            ]
            for layout, occupations in collected.measured.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if any(collected.measured.values()):
        print(render(document, trials, collected.measured, judgments))
    print(f"保存した: {path}")
    if collected.stopped is not None and not collected.over_budget:
        sys.exit(1)


def _show(args: argparse.Namespace) -> None:
    try:
        document = json.loads(args.result.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        sys.exit(f"校正の結果を読めません: {error}")
    _, judgments = _grading(args.dataset, args.judgments)
    try:
        _require_same_grading(document, args.dataset, args.judgments)
        measured = {
            Layout(name): [
                OccupationOdds(
                    occupation["occupation"],
                    tuple(CourseOdds(**odds) for odds in occupation["odds"]),
                    occupation["input_tokens"],
                )
                for occupation in occupations
            ]
            for name, occupations in document["layouts"].items()
        }
        print(render(document, selector_trials(document["trials"]), measured, judgments))
    except (KeyError, TypeError, ValueError) as error:
        sys.exit(f"校正の結果を読めません: {error!r}")


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="選び直しの判定を Jev に聞き、確率の校正と今の選び手との差を測る"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="実験の結果の候補を Jev に聞いて結果を JSON に残す")
    run.add_argument("run", type=Path)
    run.add_argument("--label", type=label, required=True)
    run.add_argument("--layout", choices=tuple(LAYOUTS), default="both")
    run.add_argument("--repeat", type=int, default=1)
    run.add_argument("--budget", type=float, default=50)
    run.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    run.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    run.set_defaults(handle=_run)
    show = commands.add_parser("show", help="残した校正の結果を出し直す")
    show.add_argument("result", type=Path)
    show.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    show.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    show.set_defaults(handle=_show)
    args = parser.parse_args(argv)
    if args.command == "run" and not (math.isfinite(args.budget) and args.budget > 0):
        parser.error("--budget は 0 より大きい数にしてください")
    if args.command == "run" and args.repeat < 1:
        parser.error("--repeat は 1 以上にしてください")
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = arguments(argv)
    args.handle(args)


if __name__ == "__main__":
    main()
