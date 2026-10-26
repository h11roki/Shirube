import argparse
import sys
from pathlib import Path

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.evaluate_search import (
    RECALL_CUTOFFS,
    EvaluateSearch,
    EvaluationError,
    EvaluationReport,
    HandwrittenProfiles,
)
from app.application.ports import EmbeddingError, OccupationAnalysisError, OccupationAnalyzer
from app.application.search_courses import SearchError
from app.presentation.cli.evaluation_data import (
    DEFAULT_DATASET,
    load_dataset,
    shown_reason,
    silence_heldout_logs,
)
from app.presentation.cli.labels import SEARCH_MODES
from app.presentation.composition import (
    database_engine,
    load_settings,
    openai_occupation_analyzer,
    search_courses,
)

HANDWRITTEN, LLM = "handwritten", "llm"
SEARCHED_WITH = {HANDWRITTEN: "評価データの職業名と手書きのスキル", LLM: "LLM の解釈とスキル"}


def render_means(report: EvaluationReport) -> str:
    means = "  ".join(f"@{cutoff} {report.mean_recall(cutoff):.2f}" for cutoff in RECALL_CUTOFFS)
    return f"平均  {means}"


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
    lines.append(render_means(report))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="職業ごとの期待する科目で検索の再現率を測る")
    parser.add_argument("dataset", type=Path, nargs="?", default=DEFAULT_DATASET)
    parser.add_argument(
        "--skills",
        choices=tuple(SEARCHED_WITH),
        default=HANDWRITTEN,
        help="検索文を評価データの職業名と手書きのスキルで作るか、LLM の解釈とスキルで作るか",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="職業ごとの結果を出さず、平均の再現率だけを出す(確かめ用はいつも平均だけ。ADR 0067)",
    )
    args = parser.parse_args()

    try:
        dataset = load_dataset(args.dataset)
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"評価データを読めません: {args.dataset}: {error!r}")
    silence_heldout_logs(dataset)
    settings = load_settings()
    profiles: OccupationAnalyzer = (
        openai_occupation_analyzer(settings) if args.skills == LLM else HandwrittenProfiles(dataset)
    )
    engine = database_engine(settings)
    search = search_courses(settings, engine)
    print(
        f"埋め込み {settings.embedding_model}、検索 {SEARCH_MODES[settings.search_by_skill]}、"
        f"検索文 {SEARCHED_WITH[args.skills]}"
    )
    try:
        report = EvaluateSearch(search, profiles).run(dataset)
        print(render_means(report) if args.summary or dataset.heldout else render(report))
    except (
        EvaluationError,
        SearchError,
        OccupationAnalysisError,
        EmbeddingError,
    ) as error:
        sys.exit(f"評価を止めました: {shown_reason(error, dataset.heldout)}")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {shown_reason(error.orig, dataset.heldout)}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {shown_reason(error, dataset.heldout)}")
    except OSError as error:
        reason = shown_reason(error, dataset.heldout)
        sys.exit(f"ネットワークかファイルの読み書きに失敗しました: {reason}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
