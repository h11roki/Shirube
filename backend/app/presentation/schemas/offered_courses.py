from pydantic import BaseModel

from app.domain.course import Term


class SemesterOut(BaseModel):
    grade: int
    term: Term


class OfferedCourseOut(BaseModel):
    name: str
    credits: int
    semesters: list[SemesterOut]


class OfferedCoursesOut(BaseModel):
    term: Term
    courses: list[OfferedCourseOut]
