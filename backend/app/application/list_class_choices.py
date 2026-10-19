from uuid import UUID

from app.application.ports import CourseRepository, UserRepository
from app.domain.course import left_out_codes
from app.domain.roadmap import ClassChoice, Semester, class_choices, remaining_semesters


class ListClassChoices:
    def __init__(self, courses: CourseRepository, users: UserRepository) -> None:
        self._courses = courses
        self._users = users

    def run(self, owner_id: UUID, department: str, year: int, start: Semester) -> list[ClassChoice]:
        sections = self._courses.sections(year)
        left_out = left_out_codes(
            sections, self._courses.syllabus_codes(year), department, self._users.taken(owner_id)
        )
        return class_choices(
            [section for section in sections if section.code not in left_out],
            department,
            year,
            remaining_semesters(start),
        )
