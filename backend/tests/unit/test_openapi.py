from tests.fakes import plan_app
from tests.openapi_document import OPENAPI_JSON, openapi_text


def test_the_frontend_has_the_current_openapi_document() -> None:
    assert OPENAPI_JSON.read_text(encoding="utf-8") == openapi_text(), (
        "API が変わりました。backend で uv run python -m tests.openapi_document を実行し、"
        "frontend で pnpm gen:api を実行してください"
    )


def test_every_error_of_the_plan_apis_is_documented_as_a_detail_sentence() -> None:
    document = plan_app().openapi()
    error = {"$ref": "#/components/schemas/ErrorOut"}

    for path, operations in document["paths"].items():
        if path == "/api/v1/health":
            continue
        for operation in operations.values():
            for status in ("401", "422", "500"):
                schema = operation["responses"][status]["content"]["application/json"]["schema"]
                assert schema == error, (path, status)
    show = document["paths"]["/api/v1/plans/{plan_id}"]["get"]["responses"]["404"]
    assert show["content"]["application/json"]["schema"] == error
    assert "HTTPValidationError" not in document["components"]["schemas"]
