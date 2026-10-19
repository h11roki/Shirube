from collections.abc import Mapping
from uuid import UUID, uuid4

from app.application.ports import CourseRepository, PlanRepository, UserRepository
from app.application.search_courses import SearchCourses
from app.domain.plan import Plan, PlanConditions
from app.domain.roadmap import Semester, remaining_semesters, require_class_choices


class RequestPlan:
    def __init__(
        self,
        search: SearchCourses,
        courses: CourseRepository,
        plans: PlanRepository,
        users: UserRepository,
        credit_limit: int,
    ) -> None:
        self._search = search
        self._courses = courses
        self._plans = plans
        self._users = users
        self._credit_limit = credit_limit

    def run(
        self,
        owner_id: UUID,
        occupation: str,
        department: str,
        year: int,
        start: Semester,
        chosen_classes: Mapping[str, str],
    ) -> Plan:
        semesters = remaining_semesters(start)
        sections = self._courses.sections(year)
        require_class_choices(sections, department, year, semesters, chosen_classes)
        self._search.candidates(year, department, semesters, self._users.taken(owner_id))
        conditions = PlanConditions(
            occupation,
            department,
            year,
            start,
            tuple(sorted(chosen_classes.items())),
            self._credit_limit,
        )
        plan = Plan(uuid4(), owner_id, conditions)
        self._plans.add(plan)
        return plan
