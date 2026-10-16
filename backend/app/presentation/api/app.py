import logging
from collections.abc import Callable
from datetime import date

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.create_plan import CreatePlan
from app.application.ports import (
    CourseSelectionError,
    EmbeddingError,
    OccupationAnalysisError,
    PlanFormatError,
    PlanRepository,
)
from app.application.search_courses import NoCandidatesError, SearchError
from app.domain.recommendation import RecommendationError
from app.domain.roadmap import ClassChoiceError, RoadmapError
from app.presentation.api import health
from app.presentation.api.plans import plans_router

API_PREFIX = "/api/v1"
SERVER_FAILURE = "サーバーで道標を扱えませんでした"
UPSTREAM_FAILURE = "推薦に使う外部のサービスの呼び出しに失敗しました。時間をおいて試してください"
INPUT_ERRORS: tuple[type[Exception], ...] = (ClassChoiceError, NoCandidatesError)
UPSTREAM_ERRORS: tuple[type[Exception], ...] = (
    EmbeddingError,
    OccupationAnalysisError,
    CourseSelectionError,
    RecommendationError,
)
SERVER_ERRORS: tuple[type[Exception], ...] = (SearchError, RoadmapError, PlanFormatError)

logger = logging.getLogger(__name__)


def _input_error(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


def _upstream_error(request: Request, error: Exception) -> JSONResponse:
    logger.error("外部のサービスの呼び出しに失敗しました", exc_info=error)
    return JSONResponse({"detail": UPSTREAM_FAILURE}, status_code=status.HTTP_502_BAD_GATEWAY)


def _server_error(request: Request, error: Exception) -> JSONResponse:
    logger.error("道標を扱えませんでした", exc_info=error)
    return _unexpected_error(request, error)


def _unexpected_error(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        {"detail": SERVER_FAILURE}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def create_app(
    create_plan: CreatePlan,
    plans: PlanRepository,
    curriculum_year: int,
    today: Callable[[], date],
) -> FastAPI:
    app = FastAPI(title="shirube")
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(plans_router(create_plan, plans, curriculum_year, today), prefix=API_PREFIX)
    for error in INPUT_ERRORS:
        app.add_exception_handler(error, _input_error)
    for error in UPSTREAM_ERRORS:
        app.add_exception_handler(error, _upstream_error)
    for error in SERVER_ERRORS:
        app.add_exception_handler(error, _server_error)
    app.add_exception_handler(Exception, _unexpected_error)

    @app.exception_handler(RequestValidationError)
    def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in problem['loc'][1:])}: {problem['msg']}"
            for problem in error.errors()
        )
        return JSONResponse(
            {"detail": f"リクエストを確かめてください: {problems}"},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    return app
