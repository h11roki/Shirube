from uuid import uuid4

from app.application.delete_account import DeleteAccount
from app.application.delete_plan import DeletePlan
from tests.builders import sample_plan
from tests.fakes import FakePlanRepository, FakeUserRepository


def test_only_the_owner_deletes_a_plan_and_it_is_no_longer_found() -> None:
    plans = FakePlanRepository()
    owner, other = uuid4(), uuid4()
    plan = sample_plan(uuid4(), owner)
    plans.store(plan)

    assert DeletePlan(plans).run(owner_id=other, plan_id=plan.id) is False
    assert DeletePlan(plans).run(owner_id=owner, plan_id=plan.id) is True
    assert plans.get_owned_by(plan.id, owner) is None
    assert DeletePlan(plans).run(owner_id=owner, plan_id=plan.id) is False


def test_leaving_forgets_the_user_and_their_taken_courses() -> None:
    users = FakeUserRepository()
    user_id = users.id_of("google-a")
    users.add_taken(user_id, "情報処理")

    DeleteAccount(users).run(user_id)

    assert users.taken(user_id) == frozenset()
    assert users.id_of("google-a") != user_id
