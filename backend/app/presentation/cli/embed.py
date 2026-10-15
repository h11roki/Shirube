import argparse
import sys

from openai import OpenAIError
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.application.embed_syllabi import EmbedError, EmbedSyllabi
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.llm.openai_embedder import OpenAIEmbedder
from app.presentation.cli.environment import load_settings
from app.presentation.cli.options import add_year_option


def main() -> None:
    parser = argparse.ArgumentParser(description="その年度のシラバスをチャンクにして埋め込む")
    add_year_option(parser)
    args = parser.parse_args()

    settings = load_settings()
    if settings.openai_api_key is None:
        sys.exit("環境変数を設定してください: OPENAI_API_KEY")
    engine = create_engine(settings.database_url)
    embedder = OpenAIEmbedder(
        settings.embedding_model, settings.embedding_dimensions, settings.openai_api_key
    )
    embed = EmbedSyllabi(SqlCourseRepository(engine), SqlChunkRepository(engine), embedder)
    try:
        report = embed.run(args.year)
    except EmbedError as error:
        sys.exit(f"埋め込みを止めました: {error}。先に ingest syllabi を実行してください")
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except OpenAIError as error:
        sys.exit(f"埋め込みの API 呼び出しに失敗しました: {error}")
    finally:
        engine.dispose()
    print(
        f"チャンク {report.chunks} 件、新しく埋め込み {report.embedded} 件、"
        f"再利用 {report.reused} 件、使われなくなった埋め込みの削除 {report.pruned} 件"
    )


if __name__ == "__main__":
    main()
