from collections.abc import Set
from uuid import UUID

from app.application.ports import CourseRepository, PlanRepository, UserRepository
from app.domain.plan import Plan
from app.domain.roadmap import place, remaining_semesters


class PlanNotFinishedError(ValueError):
    pass


class UnaskedCourseError(ValueError):
    pass


class AnswerTakenCourses:
    def __init__(
        self, plans: PlanRepository, users: UserRepository, courses: CourseRepository
    ) -> None:
        self._plans = plans
        self._users = users
        self._courses = courses

    def run(self, *, owner_id: UUID, plan_id: UUID, taken: Set[str]) -> Plan | None:
        plan = self._plans.get_owned_by(plan_id, owner_id)
        if plan is None:
            return None
        if plan.result is None:
            raise PlanNotFinishedError(f"できあがっていない道標では答えられません: {plan.status}")
        asked = plan.result.roadmap.offered_earlier
        unasked = sorted(taken - asked)
        if unasked:
            raise UnaskedCourseError(
                f"この道標でもう取ったかを聞いていない授業です: {'、'.join(unasked)}"
            )
        conditions = plan.conditions
        roadmap = place(
            plan.result.recommendation,
            self._courses.sections(conditions.year),
            conditions.department,
            conditions.year,
            remaining_semesters(conditions.start),
            conditions.credit_limit,
            dict(conditions.chosen_classes),
            taken,
        )
        again = plan.placed_again(roadmap)
        self._users.replace_taken(owner_id, asked, taken)
        if not self._plans.replace_result(again):
            raise PlanNotFinishedError(f"できあがっていない道標では答えられません: {plan.id}")
        return again
