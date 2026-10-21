from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from app.application.answer_taken_courses import (
    AnswerConflictError,
    AnswerTakenCourses,
    PlanNotFinishedError,
    PlanOutdatedError,
    UnaskedCourseError,
)
from app.domain.course import Audience
from app.domain.plan import Plan, PlanResult
from tests.builders import sample_conditions, sample_plan_asking, sample_sections
from tests.fakes import FakeCourseRepository, FakePlanRepository, FakeUserRepository

COURSES = FakeCourseRepository(sample_sections())


class ConflictingPlans(FakePlanRepository):
    def replace_result(self, plan: Plan, previous: PlanResult) -> bool:
        return False


def answering(
    owner: UUID, plans: FakePlanRepository | None = None
) -> tuple[FakePlanRepository, FakeUserRepository, Plan]:
    stored = plans or FakePlanRepository()
    plan = sample_plan_asking(uuid4(), owner)
    stored.store(plan)
    return stored, FakeUserRepository(), plan


def taken_names(plan: Plan | None) -> list[str]:
    assert plan is not None
    assert plan.result is not None
    return [course.name for course in plan.result.roadmap.taken]


def placed_names(plan: Plan | None) -> set[str]:
    assert plan is not None
    assert plan.result is not None
    return {
        placed.course.name
        for semester in plan.result.roadmap.semesters
        for placed in semester.courses
    }


def test_marking_places_the_plan_again_without_the_course_and_remembers_it() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner)

    marked = AnswerTakenCourses(plans, users, COURSES).mark(
        owner_id=owner, plan_id=plan.id, name="科目A"
    )

    assert taken_names(marked) == ["科目A"]
    assert "科目A" not in placed_names(marked)
    assert plans.get(plan.id) == marked
    assert users.remembered[owner] == {"科目A"}


def test_each_answer_starts_from_the_stored_plan_so_earlier_answers_are_kept() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner)
    answer = AnswerTakenCourses(plans, users, COURSES)

    answer.mark(owner_id=owner, plan_id=plan.id, name="科目A")
    answer.mark(owner_id=owner, plan_id=plan.id, name="科目D")
    unmarked = answer.unmark(owner_id=owner, plan_id=plan.id, name="科目A")

    assert taken_names(unmarked) == ["科目D"]
    assert "科目A" in placed_names(unmarked)
    assert users.remembered[owner] == {"科目D"}


def test_a_course_the_plan_did_not_ask_about_is_refused_and_nothing_changes() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner)

    with pytest.raises(UnaskedCourseError, match="もう取ったかを聞いていない授業です: 科目B"):
        AnswerTakenCourses(plans, users, COURSES).mark(
            owner_id=owner, plan_id=plan.id, name="科目B"
        )

    assert plans.get(plan.id) == plan
    assert users.remembered == {}


def test_an_unfinished_plan_is_refused_and_another_users_plan_is_none() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner)
    waiting = Plan(uuid4(), owner, sample_conditions())
    plans.store(waiting)
    answer = AnswerTakenCourses(plans, users, COURSES)

    with pytest.raises(PlanNotFinishedError, match="完了した道標でないと答えられません: pending"):
        answer.mark(owner_id=owner, plan_id=waiting.id, name="科目A")
    assert answer.mark(owner_id=uuid4(), plan_id=plan.id, name="科目A") is None


def test_a_plan_whose_timetable_changed_since_it_was_made_is_refused() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner)
    later_only = (Audience(2020, 2026, frozenset({3, 4}), "専門"),)
    moved = FakeCourseRepository(
        tuple(
            replace(section, audiences=later_only) if section.name == "科目D" else section
            for section in sample_sections()
        )
    )
    split = FakeCourseRepository(
        (
            *sample_sections(),
            replace(sample_sections()[0], code="10009", class_code="6A"),
        )
    )
    chosen = replace(
        plan, id=uuid4(), conditions=replace(plan.conditions, chosen_classes=(("科目A", "6Z"),))
    )
    plans.store(chosen)

    with pytest.raises(PlanOutdatedError, match="時間割表が変わった"):
        AnswerTakenCourses(plans, users, moved).mark(owner_id=owner, plan_id=plan.id, name="科目A")
    with pytest.raises(PlanOutdatedError, match="時間割表が変わった"):
        AnswerTakenCourses(plans, users, split).mark(
            owner_id=owner, plan_id=chosen.id, name="科目A"
        )
    assert plans.get(plan.id) == plan
    assert users.remembered == {}


def test_an_answer_that_lost_to_another_screen_is_refused_without_remembering_it() -> None:
    owner = uuid4()
    plans, users, plan = answering(owner, ConflictingPlans())

    with pytest.raises(AnswerConflictError, match="ほかの画面で答えが変わりました"):
        AnswerTakenCourses(plans, users, COURSES).mark(
            owner_id=owner, plan_id=plan.id, name="科目A"
        )

    assert users.remembered == {}
