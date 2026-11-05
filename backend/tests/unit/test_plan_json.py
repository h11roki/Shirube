import json
from pathlib import Path
from uuid import UUID

from app.infrastructure.db.plans import (
    CONDITIONS_JSON,
    RESULT_JSON,
    conditions_from_json,
    conditions_json,
    result_from_json,
    result_json,
)
from tests.builders import sample_plan_with_fixed, sample_plan_with_taken

PLAN_ID = UUID("8888666a-9ab0-48db-ba61-cf526a15dc0d")
VERSION_4 = Path(__file__).parents[1] / "fixtures" / "plan_v4.json"


def stored() -> dict[str, object]:
    stored: dict[str, object] = json.loads(VERSION_4.read_text(encoding="utf-8"))
    return stored


def test_the_stored_shape_of_the_conditions_and_the_version_4_result_does_not_change() -> None:
    plan = sample_plan_with_fixed(PLAN_ID)
    assert plan.result is not None

    assert {
        "conditions": conditions_json(plan.conditions),
        "result": result_json(plan.result),
    } == stored()


def test_the_stored_conditions_and_version_4_result_read_back_to_the_same_plan() -> None:
    data = stored()
    conditions = CONDITIONS_JSON.validate_python(data["conditions"], strict=True)
    result = RESULT_JSON.validate_python(data["result"], strict=True)
    plan = sample_plan_with_fixed(PLAN_ID)

    assert conditions_from_json(conditions) == plan.conditions
    assert result_from_json(result) == plan.result


def test_taken_courses_and_the_courses_offered_earlier_read_back() -> None:
    result = sample_plan_with_taken(PLAN_ID).result
    assert result is not None

    data = RESULT_JSON.validate_python(json.loads(json.dumps(result_json(result))), strict=True)

    assert data["roadmap"]["taken"] == ["科目D"]
    assert data["roadmap"]["offered_earlier"] == ["科目A", "科目D"]
    assert result_from_json(data) == result
