from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.application.list_offered_courses import ListOfferedCourses
from app.presentation.api.start_query import StartQuery, start_query
from app.presentation.schemas.errors import INVALID_RESPONSE
from app.presentation.schemas.offered_courses import (
    OfferedCourseOut,
    OfferedCoursesOut,
    SemesterOut,
)


def offered_courses_router(
    list_offered_courses: ListOfferedCourses,
    current_user: Callable[..., UUID],
    curriculum_year: int,
) -> APIRouter:
    router = APIRouter()

    @router.get("/offered-courses", responses=INVALID_RESPONSE)
    def show(
        query: Annotated[StartQuery, Depends(start_query)],
        user_id: Annotated[UUID, Depends(current_user)],
    ) -> OfferedCoursesOut:
        offered = list_offered_courses.run(user_id, query.department, curriculum_year, query.start)
        return OfferedCoursesOut(
            term=query.start.term,
            courses=[
                OfferedCourseOut(
                    name=course.name,
                    credits=course.credits,
                    semesters=[
                        SemesterOut(grade=semester.grade, term=semester.term)
                        for semester in course.semesters
                    ],
                )
                for course in offered
            ],
        )

    return router
