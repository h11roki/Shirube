import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from openai import OpenAIError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.evaluate_search import EvaluationDataset, EvaluationError
from app.application.evaluate_selection import (
    EvaluateSelection,
    Judgment,
    SelectionReport,
    SelectionResult,
    judgment_of,
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
from app.presentation.cli.evaluate import DEFAULT_DATASET, load_dataset, reject_duplicate_keys
from app.presentation.cli.recommend import RELEVANCE_LABELS

DEFAULT_JUDGMENTS = DEFAULT_DATASET.with_name("judgments.json")


def load_judgments(path: Path, dataset: EvaluationDataset) -> dict[tuple[str, str], Judgment]:
    document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    if (document["year"], document["department"]) != (dataset.year, dataset.department):
        raise ValueError("判定の年度と学科が評価データと違います")
    values = {relevance.value for relevance in Relevance}
    judgments: dict[tuple[str, str], Judgment] = {}
    for occupation in document["occupations"]:
        for course in occupation["courses"]:
            key = (occupation["name"], course["name"])
            if key in judgments:
                raise ValueError(f"同じ科目の判定が 2 回あります: {key}")
            labels = [vote["label"] for vote in course["votes"].values()]
            decision = course.get("decision")
            if not set(labels) <= values or decision not in {None, *values}:
                raise ValueError(f"票か決定の値が違います: {key}")
            judgments[key] = judgment_of(labels, decision)
    return judgments


def _summary(results: Sequence[SelectionResult]) -> list[str]:
    lines = []
    for relevance in Relevance:
        counts = {
            judgment: sum(result.count(relevance, judgment) for result in results)
            for judgment in Judgment
        }
        parts = " / ".join(f"{judgment.value} {count}" for judgment, count in counts.items())
        lines.append(f"  {RELEVANCE_LABELS[relevance]} {sum(counts.values())} 科目: {parts}")
    unsearched = sum(len(result.unsearched) for result in results)
    skipped = sum(len(result.skipped) for result in results)
    lines.append(
        f"  期待する科目 {sum(len(result.expected) for result in results)}: "
        f"中心 {sum(result.expected_as(Relevance.CORE) for result in results)} / "
        f"土台 {sum(result.expected_as(Relevance.FOUNDATION) for result in results)} / "
        f"選ばず {skipped} / 検索の上位に無い {unsearched}"
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
        if result.skipped:
            lines.append(f"  選ばなかった期待する科目: {'、'.join(result.skipped)}")
        if result.unsearched:
            lines.append(f"  検索の上位に無かった期待する科目: {'、'.join(result.unsearched)}")
    lines.append("合計")
    lines += _summary(report.results)
    picks = [pick.judgment for result in report.results for pick in result.picks]
    cores = [
        pick.judgment
        for result in report.results
        for pick in result.picks
        if pick.relevance is Relevance.CORE
    ]
    expected = sum(len(result.expected) for result in report.results)
    as_core = sum(result.expected_as(Relevance.CORE) for result in report.results)
    lines.append(
        f"  中心の適合率 {cores.count(Judgment.EXPECTED) / max(len(cores), 1):.0%}、"
        f"期待する科目を中心に選んだ割合 {as_core / max(expected, 1):.0%}、"
        f"選んだ科目のうち関係なし {picks.count(Judgment.UNRELATED) / max(len(picks), 1):.0%}"
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
