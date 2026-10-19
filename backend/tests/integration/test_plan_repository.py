import json
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, delete, insert, select, text, update
from sqlalchemy.exc import IntegrityError

from app.application.ports import PlanFormatError
from app.domain.plan import Plan, PlanStatus
from app.infrastructure.db.models import PlanRow, UserRow
from app.infrastructure.db.plans import SqlPlanRepository
from app.infrastructure.db.users import SqlUserRepository
from tests.builders import sample_conditions, sample_plan

FIXTURES = Path(__file__).parents[1] / "fixtures"
VERSION_1 = FIXTURES / "plan_v1.json"
VERSION_2 = FIXTURES / "plan_v2.json"
STALL_LIMIT = timedelta(minutes=15)


@pytest.fixture
def repository(engine: Engine) -> Iterator[SqlPlanRepository]:
    yield SqlPlanRepository(engine)
    with engine.begin() as connection:
        connection.execute(delete(PlanRow))
        connection.execute(delete(UserRow))


@pytest.fixture
def owner(engine: Engine, repository: SqlPlanRepository) -> UUID:
    return SqlUserRepository(engine).id_of("google-a")


def waiting(repository: SqlPlanRepository, owner: UUID) -> Plan:
    plan = Plan(uuid4(), owner, sample_conditions())
    repository.add(plan)
    return plan


def stored_version_2() -> dict[str, Any]:
    stored: dict[str, Any] = json.loads(VERSION_2.read_text(encoding="utf-8"))
    return stored


def test_a_saved_plan_comes_back_unchanged_with_its_owner(
    repository: SqlPlanRepository, owner: UUID
) -> None:
    succeeded = sample_plan(uuid4(), owner)
    pending = waiting(repository, owner)

    repository.add(succeeded)

    assert repository.get(succeeded.id) == succeeded
    assert repository.get(pending.id) == pending


def test_an_unknown_plan_is_none(repository: SqlPlanRepository) -> None:
    assert repository.get(uuid4()) is None


@pytest.mark.parametrize(
    ("result", "message"),
    [
        ({"version": 3}, "読めない版の道標の結果です: 3"),
        ({"recommendation": {}}, "読めない版の道標の結果です: None"),
        (["配列"], "読めない版の道標の結果です: None"),
        ({"version": 2, "recommendation": {}}, "保存した道標を読めません"),
    ],
    ids=["newer-version", "no-version", "not-an-object", "broken-result"],
)
def test_a_result_stored_in_an_unknown_shape_is_a_format_error(
    engine: Engine, repository: SqlPlanRepository, owner: UUID, result: Any, message: str
) -> None:
    plan_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            insert(PlanRow).values(
                id=plan_id,
                user_id=owner,
                status="succeeded",
                conditions=stored_version_2()["conditions"],
                result=result,
            )
        )

    with pytest.raises(PlanFormatError, match=message):
        repository.get(plan_id)


def test_values_of_the_wrong_type_are_a_format_error(
    engine: Engine, repository: SqlPlanRepository, owner: UUID
) -> None:
    stored = stored_version_2()
    stored["result"]["roadmap"]["semesters"][0]["courses"][0]["section"]["credits"] = "2"
    broken_conditions = {**stored_version_2()["conditions"], "year": "2026"}
    rows = [
        {"status": "succeeded", "conditions": stored["conditions"], "result": stored["result"]},
        {"status": "pending", "conditions": broken_conditions, "result": None},
    ]
    plan_ids = [uuid4() for _ in rows]
    with engine.begin() as connection:
        for plan_id, row in zip(plan_ids, rows, strict=True):
            connection.execute(insert(PlanRow).values(id=plan_id, user_id=owner, **row))

    for plan_id in plan_ids:
        with pytest.raises(PlanFormatError, match="保存した道標を読めません"):
            repository.get(plan_id)


def test_another_owners_plan_is_none_even_when_it_cannot_be_read(
    engine: Engine, repository: SqlPlanRepository, owner: UUID
) -> None:
    plan_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            insert(PlanRow).values(
                id=plan_id,
                user_id=owner,
                status="succeeded",
                conditions=stored_version_2()["conditions"],
                result={"version": 3},
            )
        )
    other = SqlUserRepository(engine).id_of("google-b")

    assert repository.get_owned_by(plan_id, other) is None
    with pytest.raises(PlanFormatError):
        repository.get_owned_by(plan_id, owner)


def test_a_plan_is_returned_to_its_owner(repository: SqlPlanRepository, owner: UUID) -> None:
    plan = sample_plan(uuid4(), owner)
    repository.add(plan)

    assert repository.get_owned_by(plan.id, owner) == plan


def test_the_owners_plans_are_listed_newest_first_up_to_the_limit(
    engine: Engine, repository: SqlPlanRepository, owner: UUID
) -> None:
    oldest = waiting(repository, owner)
    middle = sample_plan(uuid4(), owner)
    repository.add(middle)
    newest = waiting(repository, owner)
    waiting(repository, SqlUserRepository(engine).id_of("google-b"))
    with engine.begin() as connection:
        for minutes, plan in enumerate((oldest, middle, newest)):
            connection.execute(
                update(PlanRow)
                .where(PlanRow.id == plan.id)
                .values(created_at=text(f"now() + interval '{minutes} minutes'"))
            )

    listed = repository.list_owned_by(owner, 2)

    assert [summary.id for summary in listed] == [newest.id, middle.id]
    assert [summary.status for summary in listed] == [PlanStatus.PENDING, PlanStatus.SUCCEEDED]
    assert {(summary.occupation, summary.start) for summary in listed} == {
        ("職業", sample_conditions().start)
    }
    assert listed[0].created_at > listed[1].created_at
    assert oldest.id not in {summary.id for summary in listed}


def test_the_oldest_waiting_plan_is_claimed_once_as_running(
    engine: Engine, repository: SqlPlanRepository, owner: UUID
) -> None:
    oldest = waiting(repository, owner)
    newer = waiting(repository, owner)
    repository.add(sample_plan(uuid4(), owner))

    first = repository.claim_next()
    second = repository.claim_next()

    assert first is not None and second is not None
    assert (first.id, first.status) == (oldest.id, PlanStatus.RUNNING)
    assert (second.id, second.status) == (newer.id, PlanStatus.RUNNING)
    assert repository.claim_next() is None
    with engine.connect() as connection:
        claimed = connection.execute(
            select(PlanRow.claimed_at).where(PlanRow.id.in_([oldest.id, newer.id]))
        ).scalars()
        assert all(claimed_at is not None for claimed_at in claimed)


def test_a_waiting_plan_locked_by_another_worker_is_skipped(
    engine: Engine, repository: SqlPlanRepository, owner: UUID
) -> None:
    locked = waiting(repository, owner)
    free = waiting(repository, owner)

    with engine.connect() as other_worker, other_worker.begin():
        other_worker.execute(
            text("SELECT id FROM plans WHERE id = :id FOR UPDATE"), {"id": locked.id}
        )
        claimed = repository.claim_next()

    assert claimed is not None
    assert claimed.id == free.id


def test_a_waiting_plan_that_cannot_be_read_is_claimed_and_does_not_block_the_next(
    engine: Engine, repository: SqlPlanRepository, owner: UUID
) -> None:
    broken_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            insert(PlanRow).values(
                id=broken_id, user_id=owner, status="pending", conditions={"year": "2026"}
            )
        )
    readable = waiting(repository, owner)

    with pytest.raises(PlanFormatError, match="保存した道標を読めません"):
        repository.claim_next()
    claimed = repository.claim_next()

    assert claimed is not None
    assert claimed.id == readable.id
    with engine.connect() as connection:
        status = connection.execute(
            select(PlanRow.status).where(PlanRow.id == broken_id)
        ).scalar_one()
    assert status == "running"


def test_only_a_waiting_plan_is_claimed_by_its_id(
    repository: SqlPlanRepository, owner: UUID
) -> None:
    plan = waiting(repository, owner)
    done = sample_plan(uuid4(), owner)
    repository.add(done)

    claimed = repository.claim(plan.id)

    assert claimed is not None
    assert claimed.status is PlanStatus.RUNNING
    assert repository.claim(plan.id) is None
    assert repository.claim(done.id) is None
    assert repository.claim(uuid4()) is None


def test_a_running_plan_is_finished_once_with_its_result(
    engine: Engine, repository: SqlPlanRepository, owner: UUID
) -> None:
    plan = waiting(repository, owner)
    running = repository.claim(plan.id)
    assert running is not None
    result = sample_plan(plan.id, owner).result
    assert result is not None
    succeeded = running.succeeded(result)

    assert repository.finish(succeeded) is True
    assert repository.get(plan.id) == succeeded
    assert repository.finish(running.failed("文")) is False
    assert repository.get(plan.id) == succeeded
    with engine.connect() as connection:
        finished_at = connection.execute(
            select(PlanRow.finished_at).where(PlanRow.id == plan.id)
        ).scalar_one()
    assert finished_at is not None


def test_a_plan_that_has_not_finished_cannot_be_saved_as_finished(
    repository: SqlPlanRepository, owner: UUID
) -> None:
    plan = waiting(repository, owner)

    with pytest.raises(ValueError, match="終わっていない道標は保存し直せません: pending"):
        repository.finish(plan)


def test_plans_running_past_the_limit_fail_and_recent_ones_keep_running(
    engine: Engine, repository: SqlPlanRepository, owner: UUID
) -> None:
    stuck = waiting(repository, owner)
    recent = waiting(repository, owner)
    repository.claim(stuck.id)
    repository.claim(recent.id)
    with engine.begin() as connection:
        connection.execute(
            update(PlanRow)
            .where(PlanRow.id == stuck.id)
            .values(claimed_at=text("now() - interval '16 minutes'"))
        )

    stalled = repository.fail_stalled(STALL_LIMIT, "止まりました")

    assert stalled == [stuck.id]
    stuck_now = repository.get(stuck.id)
    recent_now = repository.get(recent.id)
    assert stuck_now is not None and recent_now is not None
    assert (stuck_now.status, stuck_now.failure) == (PlanStatus.FAILED, "止まりました")
    assert recent_now.status is PlanStatus.RUNNING


@pytest.mark.parametrize(
    "row",
    [
        {"status": "done", "result": None, "failure": None},
        {"status": "succeeded", "result": None, "failure": None},
        {"status": "pending", "result": {"version": 2}, "failure": None},
        {"status": "failed", "result": None, "failure": None},
        {"status": "running", "result": None, "failure": "文"},
    ],
    ids=[
        "unknown-status",
        "succeeded-without-result",
        "pending-with-result",
        "failed-without-failure",
        "running-with-failure",
    ],
)
def test_the_table_refuses_a_status_that_does_not_match_its_result_and_failure(
    engine: Engine, repository: SqlPlanRepository, owner: UUID, row: dict[str, Any]
) -> None:
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            insert(PlanRow).values(
                id=uuid4(), user_id=owner, conditions=stored_version_2()["conditions"], **row
            )
        )


def test_a_version_1_plan_becomes_a_succeeded_plan_with_a_version_2_result(
    engine: Engine, alembic_config: Config, repository: SqlPlanRepository, owner: UUID
) -> None:
    plan_id = uuid4()
    command.downgrade(alembic_config, "0004")
    try:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO plans (id, user_id, body) VALUES (:id, :user_id, :body)"),
                {"id": plan_id, "user_id": owner, "body": VERSION_1.read_text(encoding="utf-8")},
            )
    finally:
        command.upgrade(alembic_config, "head")

    assert repository.get(plan_id) == sample_plan(plan_id, owner)
