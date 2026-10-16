from collections.abc import Mapping
from uuid import uuid4

from app.application.ports import CourseRepository, PlanRepository
from app.application.recommend_courses import RecommendCourses
from app.domain.course import ALL_GRADES
from app.domain.plan import Plan, PlanConditions
from app.domain.roadmap import Semester, place, remaining_semesters


class CreatePlan:
    def __init__(
        self,
        recommend: RecommendCourses,
        courses: CourseRepository,
        plans: PlanRepository,
        credit_limit: int,
    ) -> None:
        self._recommend = recommend
        self._courses = courses
        self._plans = plans
        self._credit_limit = credit_limit

    def run(
        self,
        occupation: str,
        department: str,
        year: int,
        start: Semester,
        chosen_classes: Mapping[str, str],
    ) -> Plan:
        grades = {grade for grade in ALL_GRADES if grade >= start.grade}
        recommendation = self._recommend.run(occupation, year, department, grades)
        roadmap = place(
            recommendation,
            self._courses.sections(year),
            department,
            year,
            remaining_semesters(start.grade, start.term),
            self._credit_limit,
            chosen_classes,
        )
        conditions = PlanConditions(
            occupation, department, year, start, dict(chosen_classes), self._credit_limit
        )
        plan = Plan(uuid4(), conditions, recommendation, roadmap)
        self._plans.add(plan)
        return plan
