import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, insert

from app.application.ports import PlanFormatError
from app.infrastructure.db.models import PlanRow
from app.infrastructure.db.plans import SqlPlanRepository
from tests.builders import sample_plan

VERSION_1 = Path(__file__).parents[1] / "fixtures" / "plan_v1.json"


@pytest.fixture
def repository(engine: Engine) -> Iterator[SqlPlanRepository]:
    yield SqlPlanRepository(engine)
    with engine.begin() as connection:
        connection.execute(delete(PlanRow))


def test_a_saved_plan_comes_back_unchanged(repository: SqlPlanRepository) -> None:
    plan = sample_plan(uuid4())

    repository.add(plan)

    assert repository.get(plan.id) == plan


def test_an_unknown_plan_is_none(repository: SqlPlanRepository) -> None:
    assert repository.get(uuid4()) is None


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"version": 2}, "読めない版の Plan です: 2"),
        ({"conditions": {}}, "読めない版の Plan です: None"),
        (["配列"], "読めない版の Plan です: None"),
        ({"version": 1, "conditions": {}}, "保存した Plan を読めません"),
    ],
    ids=["newer-version", "no-version", "not-an-object", "broken-body"],
)
def test_a_plan_stored_in_an_unknown_shape_is_a_format_error(
    engine: Engine, repository: SqlPlanRepository, body: Any, message: str
) -> None:
    plan_id = uuid4()
    with engine.begin() as connection:
        connection.execute(insert(PlanRow).values(id=plan_id, body=body))

    with pytest.raises(PlanFormatError, match=message):
        repository.get(plan_id)


def test_a_version_1_body_with_a_value_of_the_wrong_type_is_a_format_error(
    engine: Engine, repository: SqlPlanRepository
) -> None:
    plan_id = uuid4()
    body = json.loads(VERSION_1.read_text(encoding="utf-8"))
    body["roadmap"]["semesters"][0]["courses"][0]["section"]["credits"] = "2"
    with engine.begin() as connection:
        connection.execute(insert(PlanRow).values(id=plan_id, body=body))

    with pytest.raises(PlanFormatError, match="保存した Plan を読めません"):
        repository.get(plan_id)
