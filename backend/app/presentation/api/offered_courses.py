from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.application.list_offered_courses import ListOfferedCourses
from app.domain.course import ALL_GRADES, Term
from app.domain.roadmap import DEFAULT_START_TERM, Semester
from app.presentation.schemas.errors import INVALID_RESPONSE
from app.presentation.schemas.offered_courses import (
    OfferedCourseOut,
    OfferedCoursesOut,
    SemesterOut,
)
from app.presentation.schemas.plans import DepartmentName


def offered_courses_router(
    list_offered_courses: ListOfferedCourses,
    current_user: Callable[..., UUID],
    curriculum_year: int,
) -> APIRouter:
    router = APIRouter()

    @router.get("/offered-courses", responses=INVALID_RESPONSE)
    def show(
        department: Annotated[DepartmentName, Query()],
        grade: Annotated[int, Query(ge=min(ALL_GRADES), le=max(ALL_GRADES))],
        user_id: Annotated[UUID, Depends(current_user)],
        term: Term = DEFAULT_START_TERM,
    ) -> OfferedCoursesOut:
        start = Semester(grade, term)
        return OfferedCoursesOut(
            term=start.term,
            courses=[
                OfferedCourseOut(
                    name=course.name,
                    credits=course.credits,
                    semesters=[
                        SemesterOut(grade=semester.grade, term=semester.term)
                        for semester in course.semesters
                    ],
                )
                for course in list_offered_courses.run(user_id, department, curriculum_year, start)
            ],
        )

    return router
