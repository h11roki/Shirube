import logging
from collections.abc import Callable
from datetime import date

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.answer_taken_courses import (
    AnswerTakenCourses,
    PlanNotFinishedError,
    UnaskedCourseError,
)
from app.application.build_plans import SERVER_FAILURE
from app.application.get_plan import GetPlan
from app.application.identify_user import IdentifyUser
from app.application.list_class_choices import ListClassChoices
from app.application.list_plans import ListPlans
from app.application.ports import InvalidTokenError
from app.application.request_plan import RequestPlan
from app.application.search_courses import NoCandidatesError
from app.domain.roadmap import ClassChoiceError
from app.presentation.api import health
from app.presentation.api.auth import MissingTokenError, current_user
from app.presentation.api.class_choices import class_choices_router
from app.presentation.api.plans import plans_router
from app.presentation.schemas.errors import ERROR_RESPONSES

API_PREFIX = "/api/v1"
LOGIN_REQUIRED = "ログインしてください"
INPUT_ERRORS: tuple[type[Exception], ...] = (
    ClassChoiceError,
    NoCandidatesError,
    UnaskedCourseError,
)

logger = logging.getLogger(__name__)


async def _input_error(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


async def _not_finished(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=status.HTTP_409_CONFLICT)


def _unauthorized(challenge: str) -> JSONResponse:
    return JSONResponse(
        {"detail": LOGIN_REQUIRED},
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": challenge},
    )


async def _missing_token(request: Request, error: Exception) -> JSONResponse:
    return _unauthorized("Bearer")


async def _invalid_token(request: Request, error: Exception) -> JSONResponse:
    logger.warning("JWT を断りました: %s", error)
    return _unauthorized('Bearer error="invalid_token"')


async def _unexpected_error(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        {"detail": SERVER_FAILURE}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def create_app(
    request_plan: RequestPlan,
    get_plan: GetPlan,
    list_plans: ListPlans,
    list_class_choices: ListClassChoices,
    answer_taken_courses: AnswerTakenCourses,
    identify: IdentifyUser,
    curriculum_year: int,
    today: Callable[[], date],
) -> FastAPI:
    user = current_user(identify)
    app = FastAPI(title="shirube")
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(
        plans_router(
            request_plan, get_plan, list_plans, answer_taken_courses, user, curriculum_year, today
        ),
        prefix=API_PREFIX,
        responses=ERROR_RESPONSES,
    )
    app.include_router(
        class_choices_router(list_class_choices, user, curriculum_year, today),
        prefix=API_PREFIX,
        responses=ERROR_RESPONSES,
    )
    app.add_exception_handler(MissingTokenError, _missing_token)
    app.add_exception_handler(InvalidTokenError, _invalid_token)
    for error in INPUT_ERRORS:
        app.add_exception_handler(error, _input_error)
    app.add_exception_handler(PlanNotFinishedError, _not_finished)
    app.add_exception_handler(Exception, _unexpected_error)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
        problems = "; ".join(
            f"{'.'.join(part for part in problem['loc'][1:] if isinstance(part, str)) or '本文'}"
            f": {problem['msg']}"
            for problem in error.errors()
        )
        return JSONResponse(
            {"detail": f"リクエストを確かめてください: {problems}"},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    return app
