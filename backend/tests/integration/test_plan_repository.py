from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, insert

from app.application.ports import PlanFormatError
from app.infrastructure.db.models import PlanRow
from app.infrastructure.db.plans import SqlPlanRepository
from tests.builders import sample_plan


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
