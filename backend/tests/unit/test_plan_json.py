import json
from pathlib import Path
from uuid import UUID

from app.infrastructure.db.plans import PLAN_JSON, plan_from_json, plan_json
from tests.builders import SAMPLE_OWNER, sample_plan

PLAN_ID = UUID("8888666a-9ab0-48db-ba61-cf526a15dc0d")
VERSION_1 = Path(__file__).parents[1] / "fixtures" / "plan_v1.json"


def test_the_stored_shape_of_version_1_does_not_change() -> None:
    assert plan_json(sample_plan(PLAN_ID)) == json.loads(VERSION_1.read_text(encoding="utf-8"))


def test_a_version_1_body_reads_back_to_the_same_plan() -> None:
    body = PLAN_JSON.validate_python(json.loads(VERSION_1.read_text(encoding="utf-8")), strict=True)

    assert plan_from_json(PLAN_ID, SAMPLE_OWNER, body) == sample_plan(PLAN_ID)
