from tests.fakes import plan_app
from tests.openapi_document import OPENAPI_JSON, openapi_text


def test_the_frontend_has_the_current_openapi_document() -> None:
    assert OPENAPI_JSON.read_text(encoding="utf-8") == openapi_text(), (
        "API が変わりました。backend で uv run python -m tests.openapi_document を実行し、"
        "frontend で pnpm gen:api を実行してください"
    )


def test_errors_are_documented_as_a_detail_sentence_where_they_can_happen() -> None:
    document = plan_app().openapi()
    error = {"$ref": "#/components/schemas/ErrorOut"}
    checked = 0

    for path, operations in document["paths"].items():
        for operation in operations.values():
            responses = operation["responses"]
            takes_input = "parameters" in operation or "requestBody" in operation
            assert ("422" in responses) == takes_input, path
            statuses = [*(["401", "500"] if "security" in operation else []), "422"]
            for status in (status for status in statuses if status in responses):
                assert responses[status]["content"]["application/json"]["schema"] == error
                checked += 1
    show = document["paths"]["/api/v1/plans/{plan_id}"]["get"]["responses"]["404"]
    assert show["content"]["application/json"]["schema"] == error
    assert "HTTPValidationError" not in document["components"]["schemas"]
    assert checked >= 10
