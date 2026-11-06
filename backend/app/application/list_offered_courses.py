from uuid import UUID

from app.application.left_out import left_out_for
from app.application.ports import CourseRepository, UserRepository
from app.domain.roadmap import OfferedCourse, Semester, offered_courses, remaining_semesters


class ListOfferedCourses:
    def __init__(self, courses: CourseRepository, users: UserRepository) -> None:
        self._courses = courses
        self._users = users

    def run(
        self, owner_id: UUID, department: str, year: int, start: Semester
    ) -> list[OfferedCourse]:
        sections = self._courses.sections(year)
        left_out = left_out_for(self._courses, self._users, owner_id, department, year, sections)
        return offered_courses(sections, department, year, remaining_semesters(start), left_out)
