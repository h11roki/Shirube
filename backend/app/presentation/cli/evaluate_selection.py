import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from openai import OpenAIError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.evaluate_search import EvaluationError
from app.application.evaluate_selection import (
    EvaluateSelection,
    Judgment,
    Pick,
    SelectionReport,
    SelectionResult,
)
from app.application.ports import CourseSelectionError
from app.application.search_courses import SearchCourses, SearchError
from app.domain.occupation import OccupationProfileError
from app.domain.recommendation import RecommendationError, Relevance
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.presentation.cli.environment import (
    database_engine,
    load_settings,
    openai_course_selector,
    openai_embedder,
)
from app.presentation.cli.evaluation_data import (
    DEFAULT_DATASET,
    DEFAULT_JUDGMENTS,
    load_dataset,
    load_judgments,
)
from app.presentation.cli.labels import RELEVANCE_LABELS

JUDGMENT_LABELS = {
    Judgment.EXPECTED: "期待",
    Judgment.FOUNDATION: "土台",
    Judgment.MINORITY: "少数",
    Judgment.UNRELATED: "関係なし",
}


def _ratio(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "-"


def _judged(label: str, picks: Sequence[Pick]) -> str:
    counts = Counter(pick.judgment for pick in picks)
    parts = " / ".join(f"{JUDGMENT_LABELS[judgment]} {counts[judgment]}" for judgment in Judgment)
    return f"  {label} {len(picks)} 科目、判定は {parts}"


def _summary(results: Sequence[SelectionResult]) -> list[str]:
    picks = [pick for result in results for pick in result.picks]
    lines = [
        _judged(
            RELEVANCE_LABELS[relevance], [pick for pick in picks if pick.relevance is relevance]
        )
        for relevance in Relevance
    ]
    lines.append(
        _judged(
            "中心につながらず外した土台", [pick for result in results for pick in result.unlinked]
        )
    )
    lines.append(
        f"  期待する科目 {sum(len(result.expected) for result in results)}: "
        f"中心 {sum(result.expected_as(Relevance.CORE) for result in results)} / "
        f"土台 {sum(result.expected_as(Relevance.FOUNDATION) for result in results)} / "
        f"外した {sum(len(result.expected_unlinked) for result in results)} / "
        f"選ばず {sum(len(result.skipped) for result in results)} / "
        f"検索の上位に無い {sum(len(result.unsearched) for result in results)}"
    )
    return lines


def render(report: SelectionReport) -> str:
    lines = []
    for result in report.results:
        lines.append(result.occupation)
        lines += _summary([result])
        unrelated = [pick.name for pick in result.picks if pick.judgment is Judgment.UNRELATED]
        if unrelated:
            lines.append(f"  関係なしを選んだ: {'、'.join(unrelated)}")
        if result.unlinked:
            unlinked = [f"{pick.name}(→ {pick.prerequisite_for})" for pick in result.unlinked]
            lines.append(f"  中心につながらず外した土台: {'、'.join(unlinked)}")
        if result.skipped:
            lines.append(f"  選ばなかった期待する科目: {'、'.join(result.skipped)}")
        if result.unsearched:
            lines.append(f"  検索の上位に無かった期待する科目: {'、'.join(result.unsearched)}")
    lines.append("合計")
    lines += _summary(report.results)
    picks = [pick for result in report.results for pick in result.picks]
    cores = [pick for pick in picks if pick.relevance is Relevance.CORE]
    expected = sum(len(result.expected) for result in report.results)
    as_core = sum(result.expected_as(Relevance.CORE) for result in report.results)
    core_hits = sum(1 for pick in cores if pick.judgment is Judgment.EXPECTED)
    unrelated_picks = sum(1 for pick in picks if pick.judgment is Judgment.UNRELATED)
    lines.append(
        f"  中心の適合率 {_ratio(core_hits, len(cores))}、"
        f"期待する科目を中心に選んだ割合 {_ratio(as_core, expected)}、"
        f"選んだ科目のうち関係なし {_ratio(unrelated_picks, len(picks))}"
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="選び直しの結果を判定の票と比べる")
    parser.add_argument("dataset", type=Path, nargs="?", default=DEFAULT_DATASET)
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    args = parser.parse_args()

    try:
        dataset = load_dataset(args.dataset)
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"評価データを読めません: {args.dataset}: {error!r}")
    try:
        judgments = load_judgments(args.judgments, dataset)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        sys.exit(f"判定を読めません: {args.judgments}: {error!r}")
    settings = load_settings()
    embedder = openai_embedder(settings)
    selector = openai_course_selector(settings)
    engine = database_engine(settings)
    courses = SqlCourseRepository(engine)
    search = SearchCourses(courses, SqlChunkRepository(engine), embedder)
    evaluate = EvaluateSelection(search, courses, selector, settings.selection_candidate_limit)
    try:
        print(render(evaluate.run(dataset, judgments)))
    except (
        EvaluationError,
        SearchError,
        OccupationProfileError,
        CourseSelectionError,
        RecommendationError,
    ) as error:
        sys.exit(f"評価を止めました: {error}")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    except OpenAIError as error:
        sys.exit(f"OpenAI の API 呼び出しに失敗しました: {error}")
    except OSError as error:
        sys.exit(f"ネットワークに失敗しました: {error}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
