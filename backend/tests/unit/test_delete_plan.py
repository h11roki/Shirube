from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.application.delete_account import DeleteAccount
from app.application.delete_plan import DeletePlan, PlanRunningError
from app.domain.plan import Plan, PlanStage, PlanStatus
from tests.builders import sample_conditions, sample_plan
from tests.fakes import FIRST_CREATED_AT, FakePlanRepository, FakeUserRepository

NOW = FIRST_CREATED_AT + timedelta(hours=1)


def deleting(plans: FakePlanRepository) -> DeletePlan:
    return DeletePlan(plans, lambda: NOW)


def test_only_the_owner_deletes_a_plan_and_its_time_is_kept_for_the_day() -> None:
    plans = FakePlanRepository()
    owner, other = uuid4(), uuid4()
    plan = sample_plan(uuid4(), owner)
    plans.store(plan)

    assert deleting(plans).run(owner_id=other, plan_id=plan.id) is False
    assert deleting(plans).run(owner_id=owner, plan_id=plan.id) is True
    assert plans.get_owned_by(plan.id, owner) is None
    assert plans.deleted == {plan.id: owner}
    assert deleting(plans).run(owner_id=owner, plan_id=plan.id) is False


def test_a_plan_made_before_today_leaves_nothing_behind() -> None:
    plans = FakePlanRepository()
    owner = uuid4()
    plan = sample_plan(uuid4(), owner)
    plans.store(plan)
    plans.created_at[plan.id] = datetime.fromisoformat("2026-10-18T23:59+09:00")

    assert deleting(plans).run(owner_id=owner, plan_id=plan.id) is True
    assert (plans.plans, plans.deleted) == ({}, {})


def test_a_plan_being_built_cannot_be_deleted_but_a_waiting_one_can() -> None:
    plans = FakePlanRepository()
    owner = uuid4()
    waiting = Plan(uuid4(), owner, sample_conditions())
    running = replace(
        Plan(uuid4(), owner, sample_conditions()),
        status=PlanStatus.RUNNING,
        stage=PlanStage.ANALYZING,
    )
    plans.store(waiting)
    plans.store(running)

    with pytest.raises(PlanRunningError, match="できてから消せます"):
        deleting(plans).run(owner_id=owner, plan_id=running.id)
    assert deleting(plans).run(owner_id=owner, plan_id=waiting.id) is True


def test_a_deleted_failed_plan_is_kept_without_its_owner() -> None:
    plans = FakePlanRepository()
    owner = uuid4()
    failed = replace(Plan(uuid4(), owner, sample_conditions()), status=PlanStatus.RUNNING).failed(
        "失敗"
    )
    plans.store(failed)

    deleting(plans).run(owner_id=owner, plan_id=failed.id)

    assert plans.deleted == {failed.id: None}


def test_leaving_forgets_the_user_unless_a_plan_is_being_built() -> None:
    users = FakeUserRepository()
    user_id = users.id_of("google-a")
    users.add_taken(user_id, "情報処理")
    users.building.add(user_id)

    with pytest.raises(PlanRunningError, match="できてから退会できます"):
        DeleteAccount(users, lambda: NOW).run(user_id)
    users.building.clear()
    DeleteAccount(users, lambda: NOW).run(user_id)

    assert users.taken(user_id) == frozenset()
    assert users.id_of("google-a") != user_id
