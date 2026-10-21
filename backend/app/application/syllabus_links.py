from app.application.ports import CourseRepository
from app.domain.plan import Plan


class SyllabusLinks:
    def __init__(self, courses: CourseRepository) -> None:
        self._courses = courses

    def of(self, plan: Plan) -> dict[str, str]:
        if plan.result is None:
            return {}
        codes = {course.syllabus_code for course in plan.result.recommendation.courses}
        return self._courses.syllabus_urls(plan.conditions.year, codes)
