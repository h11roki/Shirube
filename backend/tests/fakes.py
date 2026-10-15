from app.domain.course import CourseSection
from app.domain.syllabus import Syllabus


class FakeCourseRepository:
    def __init__(
        self, sections: tuple[CourseSection, ...] = (), syllabi: tuple[Syllabus, ...] = ()
    ) -> None:
        self.stored_sections = list(sections)
        self.stored_syllabi = list(syllabi)
        self.section_calls: list[tuple[int, list[CourseSection]]] = []
        self.syllabus_calls: list[tuple[int, list[Syllabus]]] = []

    def replace_sections(self, year: int, sections: list[CourseSection]) -> None:
        self.section_calls.append((year, sections))

    def replace_syllabi(self, year: int, syllabi: list[Syllabus]) -> None:
        self.syllabus_calls.append((year, syllabi))

    def sections(self, year: int) -> list[CourseSection]:
        return self.stored_sections

    def syllabi(self, year: int) -> list[Syllabus]:
        return self.stored_syllabi

    def syllabus(self, year: int, code: str) -> Syllabus | None:
        return next((page for page in self.stored_syllabi if page.code == code), None)

    def syllabus_codes(self, year: int) -> dict[str, str]:
        return {
            code: page.code
            for page in self.stored_syllabi
            for code in (page.code, *(alias.code for alias in page.aliases))
        }
