from collections.abc import Callable
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.application.create_plan import CreatePlan
from app.application.ports import PlanRepository
from app.domain.course import Term
from app.domain.roadmap import Semester, term_on
from app.presentation.schemas.plans import PlanIn, PlanOut, plan_out


def plans_router(
    create_plan: CreatePlan,
    plans: PlanRepository,
    curriculum_year: int,
    today: Callable[[], date],
) -> APIRouter:
    router = APIRouter()

    @router.post("/plans", status_code=status.HTTP_201_CREATED)
    def create(body: PlanIn, request: Request, response: Response) -> PlanOut:
        term = Term(body.term) if body.term is not None else term_on(today())
        plan = create_plan.run(
            body.occupation,
            body.department,
            curriculum_year,
            Semester(body.grade, term),
            body.chosen_classes,
        )
        response.headers["Location"] = request.app.url_path_for("show_plan", plan_id=str(plan.id))
        return plan_out(plan)

    @router.get("/plans/{plan_id}", name="show_plan")
    def show(plan_id: UUID) -> PlanOut:
        plan = plans.get(plan_id)
        if plan is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Plan がありません: {plan_id}")
        return plan_out(plan)

    return router
