from uuid import uuid4

from app.application.get_plan import GetPlan
from app.application.identify_user import IdentifyUser
from tests.builders import sample_plan
from tests.fakes import TOKENS, FakePlanRepository, FakeTokenVerifier, FakeUserRepository


def test_a_plan_is_returned_only_to_its_owner() -> None:
    plans = FakePlanRepository()
    owner, other = uuid4(), uuid4()
    plan = sample_plan(uuid4(), owner)
    plans.add(plan)

    assert GetPlan(plans).run(plan.id, owner) == plan
    assert GetPlan(plans).run(plan.id, other) is None
    assert GetPlan(plans).run(uuid4(), owner) is None


def test_the_same_subject_is_always_the_same_user() -> None:
    identify = IdentifyUser(FakeTokenVerifier(TOKENS), FakeUserRepository())

    assert identify.run("token-a") == identify.run("token-a") != identify.run("token-b")
