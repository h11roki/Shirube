from app.application.ports import CourseRepository
from app.domain.roadmap import ClassChoice, Semester, class_choices, remaining_semesters


class ListClassChoices:
    def __init__(self, courses: CourseRepository) -> None:
        self._courses = courses

    def run(self, department: str, year: int, start: Semester) -> list[ClassChoice]:
        return class_choices(
            self._courses.sections(year), department, year, remaining_semesters(start)
        )
