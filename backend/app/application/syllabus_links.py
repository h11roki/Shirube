from collections.abc import Mapping
from dataclasses import dataclass, field

from app.application.ports import CourseRepository
from app.domain.plan import Plan


@dataclass(frozen=True)
class PlanLinks:
    urls: Mapping[str, str] = field(default_factory=dict)
    section_pages: Mapping[str, str] = field(default_factory=dict)

    def page_of(self, section_code: str, course_page: str | None) -> str | None:
        return self.section_pages.get(section_code, course_page)


class SyllabusLinks:
    def __init__(self, courses: CourseRepository) -> None:
        self._courses = courses

    def of(self, plan: Plan) -> PlanLinks:
        if plan.result is None:
            return PlanLinks()
        year = plan.conditions.year
        roadmap = plan.result.roadmap
        page_of = self._courses.syllabus_codes(year)
        placed = {
            course.section.code
            for semester in roadmap.semesters
            for course in (*semester.courses, *semester.continuing)
        }
        section_pages = {code: page_of[code] for code in placed if code in page_of}
        course_pages = {course.syllabus_code for course in plan.result.recommendation.courses} | {
            course.syllabus_code for course in roadmap.fixed if course.syllabus_code is not None
        }
        urls = self._courses.syllabus_urls(year, course_pages | set(section_pages.values()))
        return PlanLinks(urls, section_pages)
