import sys

from pydantic import ValidationError

from app.settings import Settings


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        problems = "; ".join(
            f"{str(problem['loc'][0]).upper() if problem['loc'] else '設定'}: {problem['msg']}"
            for problem in error.errors()
        )
        sys.exit(f"環境変数を確かめてください: {problems}")
