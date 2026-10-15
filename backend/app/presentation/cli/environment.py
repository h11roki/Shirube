import sys

from pydantic import ValidationError

from app.settings import Settings


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        names = ", ".join(str(problem["loc"][0]).upper() for problem in error.errors())
        sys.exit(f"環境変数を設定してください: {names}")
