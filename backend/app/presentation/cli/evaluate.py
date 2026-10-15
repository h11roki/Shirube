import argparse
import json
import sys
from pathlib import Path

from openai import OpenAIError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.evaluate_search import (
    RECALL_CUTOFFS,
    EvaluateSearch,
    EvaluationCase,
    EvaluationDataset,
    EvaluationError,
    EvaluationReport,
)
from app.application.search_courses import SearchCourses
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.presentation.cli.environment import database_engine, load_settings, openai_embedder

DEFAULT_DATASET = Path("eval/occupations.json")


def load_dataset(path: Path) -> EvaluationDataset:
    document = json.loads(path.read_text(encoding="utf-8"))
    return EvaluationDataset(
        year=int(document["year"]),
        department=str(document["department"]),
        cases=tuple(
            EvaluationCase(
                occupation=str(occupation["name"]),
                skills=tuple(str(skill) for skill in occupation["skills"]),
                expected=tuple(str(name) for name in occupation["expected"]),
            )
            for occupation in document["occupations"]
        ),
    )


def render(report: EvaluationReport) -> str:
    lines = []
    for result in report.results:
        recalls = "  ".join(f"@{cutoff} {result.recall(cutoff):.2f}" for cutoff in RECALL_CUTOFFS)
        lines.append(f"{result.occupation}  {recalls}")
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
    args = parser.parse_args()

    try:
        dataset = load_dataset(args.dataset)
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"評価データを読めません: {args.dataset}: {error!r}")
    settings = load_settings()
    embedder = openai_embedder(settings)
    engine = database_engine(settings)
    search = SearchCourses(SqlCourseRepository(engine), SqlChunkRepository(engine), embedder)
    try:
        print(render(EvaluateSearch(search).run(dataset)))
    except EvaluationError as error:
        sys.exit(f"評価を止めました: {error}")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    except OpenAIError as error:
        sys.exit(f"埋め込みの API 呼び出しに失敗しました: {error}")
    except OSError as error:
        sys.exit(f"ネットワークかファイルの読み書きに失敗しました: {error}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
