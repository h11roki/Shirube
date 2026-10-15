import argparse
import sys

from openai import OpenAIError
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.embed_syllabi import EmbedError, EmbedSyllabi, PruneRefusedError
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.presentation.cli.environment import database_engine, load_settings, openai_embedder
from app.presentation.cli.options import add_year_option


def main() -> None:
    parser = argparse.ArgumentParser(description="その年度のシラバスをチャンクにして埋め込む")
    add_year_option(parser)
    parser.add_argument(
        "--prune",
        action="store_true",
        help="最後に、今のモデル以外と、どのチャンクからも引かれない埋め込みを消す",
    )
    args = parser.parse_args()

    settings = load_settings()
    embedder = openai_embedder(settings)
    engine = database_engine(settings)
    embed = EmbedSyllabi(SqlCourseRepository(engine), SqlChunkRepository(engine), embedder)
    try:
        report = embed.run(args.year)
        print(
            f"チャンク {report.chunks} 件、本文 {report.texts} 種類のうち"
            f"新しく埋め込み {report.embedded} 件、再利用 {report.reused} 件"
        )
        if args.prune:
            print(f"使われなくなった埋め込みの削除 {embed.prune()} 件")
    except EmbedError as error:
        sys.exit(f"埋め込みを止めました: {error}")
    except PruneRefusedError as error:
        sys.exit(f"埋め込みは済みましたが、削除はしませんでした: {error}")
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
