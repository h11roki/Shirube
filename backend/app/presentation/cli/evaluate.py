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
from app.application.search_courses import SearchCourses, SearchError
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.presentation.cli.environment import database_engine, load_settings, openai_embedder

DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "eval" / "occupations.json"


def load_dataset(path: Path) -> EvaluationDataset:
    document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
    cases = []
    for occupation in document["occupations"]:
        name, skills, expected = occupation["name"], occupation["skills"], occupation["expected"]
        if not isinstance(skills, list) or not skills or not all(_text(skill) for skill in skills):
            raise ValueError(f"{name}: skills は空でない文字列の配列にしてください")
        if not isinstance(expected, dict) or not all(_text(why) for why in expected.values()):
            raise ValueError(
                f"{name}: expected は科目名から理由(空でない文字列)への対応にしてください"
            )
        cases.append(EvaluationCase(str(name), tuple(skills), tuple(expected)))
    names = [case.occupation for case in cases]
    duplicated = sorted({name for name in names if names.count(name) > 1})
    if duplicated:
        raise ValueError(f"同じ職業が 2 回あります: {'、'.join(duplicated)}")
    return EvaluationDataset(int(document["year"]), str(document["department"]), tuple(cases))


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    duplicated = sorted({key for key in keys if keys.count(key) > 1})
    if duplicated:
        raise ValueError(f"同じ項目が 2 回あります: {'、'.join(duplicated)}")
    return dict(pairs)


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
    except (EvaluationError, SearchError) as error:
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
