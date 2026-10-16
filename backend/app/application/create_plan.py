from collections.abc import Mapping
from uuid import uuid4

from app.application.ports import CourseRepository, PlanRepository
from app.application.recommend_courses import RecommendCourses
from app.domain.plan import Plan, PlanConditions
from app.domain.roadmap import Semester, place, remaining_semesters, require_class_choices


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
        semesters = remaining_semesters(start)
        sections = self._courses.sections(year)
        require_class_choices(sections, department, year, semesters, chosen_classes)
        recommendation = self._recommend.run(occupation, year, department, semesters)
        roadmap = place(
            recommendation,
            sections,
            department,
            year,
            semesters,
            self._credit_limit,
            chosen_classes,
        )
        conditions = PlanConditions(
            occupation,
            department,
            year,
            start,
            tuple(sorted(chosen_classes.items())),
            self._credit_limit,
        )
        plan = Plan(uuid4(), conditions, recommendation, roadmap)
        self._plans.add(plan)
        return plan
