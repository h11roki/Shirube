import importlib
import sys

import pytest
from fastapi.testclient import TestClient


def test_the_app_is_composed_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AUTH_JWT_SECRET", "s" * 32)
    monkeypatch.setenv("CURRICULUM_YEAR", "2031")
    sys.modules.pop("app.main", None)

    main = importlib.import_module("app.main")

    assert TestClient(main.app).get("/api/v1/health").json() == {"status": "ok"}
    assert set(main.app.openapi()["paths"]) >= {"/api/v1/plans", "/api/v1/plans/{plan_id}"}
    assert main.settings.curriculum_year == 2031


@pytest.mark.parametrize(
    ("secret", "message"),
    [(None, "AUTH_JWT_SECRET が設定されていません"), ("s" * 31, "32 文字以上")],
    ids=["missing", "too-short"],
)
def test_the_app_does_not_start_without_a_long_enough_jwt_secret(
    monkeypatch: pytest.MonkeyPatch, secret: str | None, message: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    if secret is not None:
        monkeypatch.setenv("AUTH_JWT_SECRET", secret)
    sys.modules.pop("app.main", None)

    with pytest.raises(SystemExit, match=message):
        importlib.import_module("app.main")
