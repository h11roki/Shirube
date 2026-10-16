import argparse
import sys
from pathlib import Path

from openai import OpenAIError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.evaluate_search import (
    RECALL_CUTOFFS,
    EvaluateSearch,
    EvaluationError,
    EvaluationReport,
    with_analyzed_skills,
)
from app.application.ports import OccupationAnalysisError
from app.application.search_courses import SearchCourses, SearchError
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.presentation.cli.evaluation_data import DEFAULT_DATASET, load_dataset
from app.presentation.composition import (
    database_engine,
    load_settings,
    openai_embedder,
    openai_occupation_analyzer,
)

HANDWRITTEN, LLM = "handwritten", "llm"


def render(report: EvaluationReport) -> str:
    lines = []
    for result in report.results:
        recalls = "  ".join(f"@{cutoff} {result.recall(cutoff):.2f}" for cutoff in RECALL_CUTOFFS)
        lines.append(f"{result.occupation}  {recalls}")
        lines.append(f"  検索文: {' / '.join(result.query.splitlines())}")
        ranks = " / ".join(
            f"{name} {f'{rank} 位' if rank is not None else '圏外'}" for name, rank in result.ranks
        )
        lines.append(f"  {ranks}")
    means = "  ".join(f"@{cutoff} {report.mean_recall(cutoff):.2f}" for cutoff in RECALL_CUTOFFS)
    lines.append(f"平均  {means}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="職業ごとの期待する科目で検索の再現率を測る")
    parser.add_argument("dataset", type=Path, nargs="?", default=DEFAULT_DATASET)
    parser.add_argument(
        "--skills",
        choices=(HANDWRITTEN, LLM),
        default=HANDWRITTEN,
        help="検索文のスキルを評価データの手書きにするか、職業名から LLM に出させるか",
    )
    args = parser.parse_args()

    try:
        dataset = load_dataset(args.dataset)
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"評価データを読めません: {args.dataset}: {error!r}")
    settings = load_settings()
    embedder = openai_embedder(settings)
    analyzer = openai_occupation_analyzer(settings) if args.skills == LLM else None
    engine = database_engine(settings)
    search = SearchCourses(SqlCourseRepository(engine), SqlChunkRepository(engine), embedder)
    try:
        if analyzer is not None:
            dataset = with_analyzed_skills(dataset, analyzer)
        print(render(EvaluateSearch(search).run(dataset)))
    except (
        EvaluationError,
        SearchError,
        OccupationAnalysisError,
    ) as error:
        sys.exit(f"評価を止めました: {error}")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    except OpenAIError as error:
        sys.exit(f"OpenAI の API 呼び出しに失敗しました: {error}")
    except OSError as error:
        sys.exit(f"ネットワークかファイルの読み書きに失敗しました: {error}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
