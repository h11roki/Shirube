from collections.abc import Callable
from datetime import date

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.application.create_plan import CreatePlan
from app.application.ports import (
    CourseSelectionError,
    OccupationAnalysisError,
    PlanFormatError,
    PlanRepository,
)
from app.application.search_courses import SearchError
from app.domain.recommendation import RecommendationError
from app.domain.roadmap import RoadmapError
from app.presentation.api import health
from app.presentation.api.plans import plans_router

API_PREFIX = "/api/v1"


def _respond_with(status_code: int) -> Callable[[Request, Exception], JSONResponse]:
    def respond(request: Request, error: Exception) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=status_code)

    return respond


upstream_failure = _respond_with(status.HTTP_502_BAD_GATEWAY)

ERROR_STATUS = {
    RoadmapError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    SearchError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    OccupationAnalysisError: status.HTTP_502_BAD_GATEWAY,
    CourseSelectionError: status.HTTP_502_BAD_GATEWAY,
    RecommendationError: status.HTTP_502_BAD_GATEWAY,
    PlanFormatError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def create_app(
    create_plan: CreatePlan,
    plans: PlanRepository,
    curriculum_year: int,
    today: Callable[[], date],
) -> FastAPI:
    app = FastAPI(title="shirube")
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(plans_router(create_plan, plans, curriculum_year, today), prefix=API_PREFIX)
    for error, status_code in ERROR_STATUS.items():
        app.add_exception_handler(error, _respond_with(status_code))
    return app
