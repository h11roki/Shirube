from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.application.forget_taken_course import ForgetTakenCourse
from app.application.list_taken_courses import ListTakenCourses
from app.presentation.schemas.errors import INVALID_RESPONSE
from app.presentation.schemas.taken_courses import TakenCourseName, TakenCoursesOut


def taken_courses_router(
    list_taken_courses: ListTakenCourses,
    forget_taken_course: ForgetTakenCourse,
    current_user: Callable[..., UUID],
) -> APIRouter:
    router = APIRouter()

    @router.get("/taken-courses")
    def index(user_id: Annotated[UUID, Depends(current_user)]) -> TakenCoursesOut:
        return TakenCoursesOut(names=list_taken_courses.run(user_id))

    @router.delete("/taken-courses/{name:path}", responses=INVALID_RESPONSE)
    def forget(
        name: TakenCourseName, user_id: Annotated[UUID, Depends(current_user)]
    ) -> TakenCoursesOut:
        forget_taken_course.run(user_id, name)
        return TakenCoursesOut(names=list_taken_courses.run(user_id))

    return router
