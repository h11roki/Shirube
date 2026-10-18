from tests.openapi_document import OPENAPI_JSON, openapi_text


def test_the_frontend_has_the_current_openapi_document() -> None:
    assert OPENAPI_JSON.read_text(encoding="utf-8") == openapi_text(), (
        "API が変わりました。backend で uv run python -m tests.openapi_document を実行し、"
        "frontend で pnpm gen:api を実行してください"
    )
