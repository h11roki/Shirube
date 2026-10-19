from uuid import UUID

from app.application.ports import CourseRepository, UserRepository
from app.domain.roadmap import ClassChoice, Semester, class_choices, remaining_semesters


class ListClassChoices:
    def __init__(self, courses: CourseRepository, users: UserRepository) -> None:
        self._courses = courses
        self._users = users

    def run(self, owner_id: UUID, department: str, year: int, start: Semester) -> list[ClassChoice]:
        taken = self._users.taken(owner_id)
        sections = [
            section for section in self._courses.sections(year) if section.name not in taken
        ]
        return class_choices(sections, department, year, remaining_semesters(start))
