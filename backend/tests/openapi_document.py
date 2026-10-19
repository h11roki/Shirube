import json
from pathlib import Path

from tests.fakes import plan_app

OPENAPI_JSON = Path(__file__).parents[2] / "frontend" / "src" / "lib" / "api" / "openapi.json"


def openapi_text() -> str:
    return json.dumps(plan_app().openapi(), ensure_ascii=False, indent=2) + "\n"


if __name__ == "__main__":
    OPENAPI_JSON.write_text(openapi_text(), encoding="utf-8")
