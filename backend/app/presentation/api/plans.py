from collections.abc import Callable
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.create_plan import CreatePlan
from app.application.get_plan import GetPlan
from app.application.identify_user import IdentifyUser
from app.domain.roadmap import Semester, term_on
from app.presentation.schemas.plans import PlanIn, PlanOut, plan_out


class MissingTokenError(Exception):
    pass


def plans_router(
    create_plan: CreatePlan,
    get_plan: GetPlan,
    identify: IdentifyUser,
    curriculum_year: int,
    today: Callable[[], date],
) -> APIRouter:
    router = APIRouter()
    bearer = HTTPBearer(auto_error=False)

    def current_user(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> UUID:
        if credentials is None:
            raise MissingTokenError("Authorization に Bearer の JWT がありません")
        return identify.run(credentials.credentials)

    @router.post("/plans", status_code=status.HTTP_201_CREATED)
    def create(
        body: PlanIn,
        user_id: Annotated[UUID, Depends(current_user)],
        request: Request,
        response: Response,
    ) -> PlanOut:
        term = body.term or term_on(today())
        plan = create_plan.run(
            user_id,
            body.occupation,
            body.department,
            curriculum_year,
            Semester(body.grade, term),
            body.chosen_classes,
        )
        response.headers["Location"] = request.app.url_path_for("show_plan", plan_id=str(plan.id))
        return plan_out(plan)

    @router.get("/plans/{plan_id}", name="show_plan")
    def show(plan_id: UUID, user_id: Annotated[UUID, Depends(current_user)]) -> PlanOut:
        plan = get_plan.run(plan_id, user_id)
        if plan is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Plan がありません: {plan_id}")
        return plan_out(plan)

    return router
