from dataclasses import replace
from uuid import uuid4

import pytest

from app.application.delete_account import DeleteAccount
from app.application.delete_plan import DeletePlan, PlanRunningError
from app.domain.plan import Plan, PlanStage, PlanStatus
from tests.builders import sample_conditions, sample_plan
from tests.fakes import FakePlanRepository, FakeUserRepository


def test_only_the_owner_deletes_a_plan_and_it_is_no_longer_found() -> None:
    plans = FakePlanRepository()
    owner, other = uuid4(), uuid4()
    plan = sample_plan(uuid4(), owner)
    plans.store(plan)

    assert DeletePlan(plans).run(owner_id=other, plan_id=plan.id) is False
    assert DeletePlan(plans).run(owner_id=owner, plan_id=plan.id) is True
    assert plans.get_owned_by(plan.id, owner) is None
    assert plans.deleted == {plan.id: owner}
    assert DeletePlan(plans).run(owner_id=owner, plan_id=plan.id) is False


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
        DeletePlan(plans).run(owner_id=owner, plan_id=running.id)
    assert DeletePlan(plans).run(owner_id=owner, plan_id=waiting.id) is True


def test_a_deleted_failed_plan_is_kept_without_its_owner() -> None:
    plans = FakePlanRepository()
    owner = uuid4()
    failed = replace(Plan(uuid4(), owner, sample_conditions()), status=PlanStatus.RUNNING).failed(
        "失敗"
    )
    plans.store(failed)

    DeletePlan(plans).run(owner_id=owner, plan_id=failed.id)

    assert plans.deleted == {failed.id: None}


def test_leaving_forgets_the_user_and_keeps_only_ownerless_times_of_their_plans() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    user_id = users.id_of("google-a")
    users.add_taken(user_id, "情報処理")
    kept, earlier = sample_plan(uuid4(), user_id), sample_plan(uuid4(), user_id)
    plans.store(kept)
    plans.store(earlier)
    plans.delete_owned_by(earlier.id, user_id)

    DeleteAccount(plans, users).run(user_id)

    assert plans.plans == {}
    assert plans.deleted == {kept.id: None, earlier.id: None}
    assert users.taken(user_id) == frozenset()
    assert users.id_of("google-a") != user_id
