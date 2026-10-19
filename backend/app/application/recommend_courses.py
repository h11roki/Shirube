from collections.abc import Callable, Sequence

from app.application.ports import CourseRepository, CourseSelector, OccupationAnalyzer
from app.application.search_courses import SearchCourses, SearchError
from app.domain.plan import PlanStage
from app.domain.recommendation import (
    CandidateCourse,
    Recommendation,
    arrange,
)
from app.domain.roadmap import Semester


class RecommendCourses:
    def __init__(
        self,
        search: SearchCourses,
        courses: CourseRepository,
        analyzer: OccupationAnalyzer,
        selector: CourseSelector,
        candidate_limit: int,
    ) -> None:
        self._search = search
        self._courses = courses
        self._analyzer = analyzer
        self._selector = selector
        self._candidate_limit = candidate_limit

    def run(
        self,
        occupation: str,
        year: int,
        department: str,
        semesters: Sequence[Semester],
        enter: Callable[[PlanStage], None] = lambda stage: None,
    ) -> Recommendation:
        candidates = self._search.candidates(year, department, semesters)
        enter(PlanStage.ANALYZING)
        profile = self._analyzer.analyze(occupation)
        enter(PlanStage.SEARCHING)
        [matches] = candidates.rank([profile.query], self._candidate_limit)
        if not matches:
            return Recommendation(profile, (), ())
        codes = {match.syllabus_code for match in matches}
        pages = self._courses.syllabi_of(year, codes)
        missing = sorted(codes - pages.keys())
        if missing:
            raise SearchError(f"シラバスが DB にありません: {'、'.join(missing)}")
        offered = [CandidateCourse(match.name, pages[match.syllabus_code]) for match in matches]
        enter(PlanStage.SELECTING)
        return arrange(profile, matches, self._selector.select(profile, offered))
