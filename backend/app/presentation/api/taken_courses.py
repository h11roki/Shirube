from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from app.application.taken_courses import TakenCourses
from app.presentation.schemas.errors import INVALID_RESPONSE
from app.presentation.schemas.plans import MAX_NAME_LENGTH
from app.presentation.schemas.taken_courses import TakenCoursesOut

TakenCourseName = Annotated[str, Path(min_length=1, max_length=MAX_NAME_LENGTH)]


def taken_courses_router(
    taken_courses: TakenCourses, current_user: Callable[..., UUID]
) -> APIRouter:
    router = APIRouter()

    @router.get("/taken-courses")
    def index(user_id: Annotated[UUID, Depends(current_user)]) -> TakenCoursesOut:
        return TakenCoursesOut(names=taken_courses.names(user_id))

    @router.delete("/taken-courses/{name:path}", responses=INVALID_RESPONSE)
    def forget(
        name: TakenCourseName, user_id: Annotated[UUID, Depends(current_user)]
    ) -> TakenCoursesOut:
        return TakenCoursesOut(names=taken_courses.forget(user_id, name))

    return router
