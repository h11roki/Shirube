from uuid import UUID, uuid4

import pytest

from app.application.answer_taken_courses import (
    AnswerTakenCourses,
    PlanNotFinishedError,
    UnaskedCourseError,
)
from app.domain.plan import Plan
from tests.builders import sample_conditions, sample_plan_asking
from tests.fakes import FakePlanRepository, FakeUserRepository, courses_ranked_by

COURSES, _ = courses_ranked_by({"科目A": 0.9, "科目B": 0.8, "科目C": 0.7, "科目D": 0.6})


def answering(owner: UUID) -> tuple[FakePlanRepository, FakeUserRepository, Plan]:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    plan = sample_plan_asking(uuid4(), owner)
    plans.add(plan)
    return plans, users, plan


def placed_names(plan: Plan) -> set[str]:
    assert plan.result is not None
    return {
        placed.course.name
        for semester in plan.result.roadmap.semesters
        for placed in semester.courses
    }


def test_answering_remembers_the_taken_course_and_places_the_plan_again_without_it() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner)
    users.replace_taken(owner, {"科目Z"}, {"科目Z"})

    again = AnswerTakenCourses(plans, users, COURSES).run(
        owner_id=owner, plan_id=plan.id, taken={"科目A"}
    )

    assert again is not None
    assert again.result is not None
    assert [course.name for course in again.result.roadmap.taken] == ["科目A"]
    assert "科目A" not in placed_names(again)
    assert plans.get(plan.id) == again
    assert users.taken[owner] == {"科目A", "科目Z"}


def test_answering_again_without_the_course_puts_it_back() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner)
    answer = AnswerTakenCourses(plans, users, COURSES)
    answer.run(owner_id=owner, plan_id=plan.id, taken={"科目A"})

    again = answer.run(owner_id=owner, plan_id=plan.id, taken=set())

    assert again is not None
    assert again.result is not None
    assert again.result.roadmap.taken == ()
    assert "科目A" in placed_names(again)
    assert users.taken[owner] == set()


def test_a_course_the_plan_did_not_ask_about_is_refused_and_nothing_changes() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner)

    with pytest.raises(UnaskedCourseError, match="もう取ったかを聞いていない授業です: 科目B"):
        AnswerTakenCourses(plans, users, COURSES).run(
            owner_id=owner, plan_id=plan.id, taken={"科目A", "科目B"}
        )

    assert plans.get(plan.id) == plan
    assert users.taken == {}


def test_an_unfinished_plan_cannot_be_answered_and_another_users_plan_is_none() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner)
    waiting = Plan(uuid4(), owner, sample_conditions())
    plans.add(waiting)
    answer = AnswerTakenCourses(plans, users, COURSES)

    with pytest.raises(PlanNotFinishedError, match="できあがっていない道標では答えられません"):
        answer.run(owner_id=owner, plan_id=waiting.id, taken=set())
    assert answer.run(owner_id=uuid4(), plan_id=plan.id, taken={"科目A"}) is None
