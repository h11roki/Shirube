from uuid import uuid4

from app.application.get_plan import GetPlan
from tests.builders import sample_plan
from tests.fakes import FakePlanRepository


def test_a_plan_is_returned_only_to_its_owner() -> None:
    plans = FakePlanRepository()
    owner, other = uuid4(), uuid4()
    plan = sample_plan(uuid4(), owner)
    plans.add(plan)

    assert GetPlan(plans).run(owner_id=owner, plan_id=plan.id) == plan
    assert GetPlan(plans).run(owner_id=other, plan_id=plan.id) is None
    assert GetPlan(plans).run(owner_id=owner, plan_id=uuid4()) is None
