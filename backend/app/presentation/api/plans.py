from collections.abc import Callable
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.application.answer_taken_courses import AnswerTakenCourses
from app.application.get_plan import GetPlan
from app.application.list_plans import ListPlans
from app.application.request_plan import RequestPlan
from app.domain.plan import Plan
from app.domain.roadmap import Semester, term_on
from app.presentation.schemas.errors import CONFLICT_RESPONSE, INVALID_RESPONSE, NOT_FOUND_RESPONSE
from app.presentation.schemas.plans import (
    PlanIn,
    PlanListOut,
    PlanOut,
    PlanSummaryOut,
    plan_out,
)
from app.presentation.schemas.taken_courses import TakenCourseName

TAKEN_COURSE = "/plans/{plan_id}/taken-courses/{name:path}"
TAKEN_RESPONSES = {**INVALID_RESPONSE, **NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE}


def _found(plan_id: UUID, plan: Plan | None) -> PlanOut:
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Plan がありません: {plan_id}")
    return plan_out(plan)


def plans_router(
    request_plan: RequestPlan,
    get_plan: GetPlan,
    list_plans: ListPlans,
    answer_taken_courses: AnswerTakenCourses,
    current_user: Callable[..., UUID],
    curriculum_year: int,
    today: Callable[[], date],
) -> APIRouter:
    router = APIRouter()

    @router.post("/plans", status_code=status.HTTP_202_ACCEPTED, responses=INVALID_RESPONSE)
    def create(
        body: PlanIn,
        user_id: Annotated[UUID, Depends(current_user)],
        request: Request,
        response: Response,
    ) -> PlanOut:
        term = body.term or term_on(today())
        plan = request_plan.run(
            user_id,
            body.occupation,
            body.department,
            curriculum_year,
            Semester(body.grade, term),
            body.chosen_classes,
        )
        response.headers["Location"] = request.app.url_path_for("show_plan", plan_id=str(plan.id))
        return plan_out(plan)

    @router.get("/plans")
    def index(user_id: Annotated[UUID, Depends(current_user)]) -> PlanListOut:
        return PlanListOut(
            plans=[
                PlanSummaryOut(
                    id=summary.id,
                    status=summary.status,
                    occupation=summary.occupation,
                    grade=summary.start.grade,
                    term=summary.start.term,
                    created_at=summary.created_at,
                )
                for summary in list_plans.run(user_id)
            ]
        )

    @router.get(
        "/plans/{plan_id}",
        name="show_plan",
        responses={**INVALID_RESPONSE, **NOT_FOUND_RESPONSE},
    )
    def show(plan_id: UUID, user_id: Annotated[UUID, Depends(current_user)]) -> PlanOut:
        return _found(plan_id, get_plan.run(owner_id=user_id, plan_id=plan_id))

    @router.put(TAKEN_COURSE, responses=TAKEN_RESPONSES)
    def mark_taken(
        plan_id: UUID, name: TakenCourseName, user_id: Annotated[UUID, Depends(current_user)]
    ) -> PlanOut:
        return _found(
            plan_id, answer_taken_courses.mark(owner_id=user_id, plan_id=plan_id, name=name)
        )

    @router.delete(TAKEN_COURSE, responses=TAKEN_RESPONSES)
    def unmark_taken(
        plan_id: UUID, name: TakenCourseName, user_id: Annotated[UUID, Depends(current_user)]
    ) -> PlanOut:
        return _found(
            plan_id, answer_taken_courses.unmark(owner_id=user_id, plan_id=plan_id, name=name)
        )

    return router
