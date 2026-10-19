from collections.abc import Callable
from uuid import UUID

from app.application.ports import CourseRepository, PlanRepository, UserRepository
from app.domain.plan import Plan
from app.domain.roadmap import ClassChoiceError, place, remaining_semesters

OUTDATED = "時間割表が変わったので、この道標は置き直せません。道標を作り直してください"
CONFLICTED = "ほかの画面で答えが変わりました。読み込み直してから答えてください"


class PlanNotFinishedError(ValueError):
    pass


class PlanOutdatedError(ValueError):
    pass


class AnswerConflictError(ValueError):
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

    def mark(self, *, owner_id: UUID, plan_id: UUID, name: str) -> Plan | None:
        return self._answer(
            owner_id, plan_id, name, lambda taken: taken | {name}, self._users.add_taken
        )

    def unmark(self, *, owner_id: UUID, plan_id: UUID, name: str) -> Plan | None:
        return self._answer(
            owner_id, plan_id, name, lambda taken: taken - {name}, self._users.remove_taken
        )

    def _answer(
        self,
        owner_id: UUID,
        plan_id: UUID,
        name: str,
        change: Callable[[frozenset[str]], frozenset[str]],
        remember: Callable[[UUID, str], None],
    ) -> Plan | None:
        plan = self._plans.get_owned_by(plan_id, owner_id)
        if plan is None:
            return None
        if plan.result is None:
            raise PlanNotFinishedError(f"完了した道標でないと答えられません: {plan.status}")
        roadmap = plan.result.roadmap
        if name not in roadmap.offered_earlier:
            raise UnaskedCourseError(f"この道標でもう取ったかを聞いていない授業です: {name}")
        conditions = plan.conditions
        try:
            again = place(
                plan.result.recommendation,
                self._courses.sections(conditions.year),
                conditions.department,
                conditions.year,
                remaining_semesters(conditions.start),
                conditions.credit_limit,
                dict(conditions.chosen_classes),
                change(frozenset(course.name for course in roadmap.taken)),
            )
        except ClassChoiceError as error:
            raise PlanOutdatedError(OUTDATED) from error
        if again.offered_earlier != roadmap.offered_earlier:
            raise PlanOutdatedError(OUTDATED)
        answered = plan.placed_again(again)
        if not self._plans.replace_result(answered, plan.result):
            raise AnswerConflictError(CONFLICTED)
        remember(owner_id, name)
        return answered
