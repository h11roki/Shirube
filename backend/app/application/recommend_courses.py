from collections.abc import Set

from app.application.ports import CourseRepository, CourseSelector, OccupationAnalyzer
from app.application.search_courses import SearchCourses
from app.domain.recommendation import (
    CandidateCourse,
    Recommendation,
    RecommendationError,
    arrange,
)


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

    def run(self, occupation: str, year: int, department: str, grades: Set[int]) -> Recommendation:
        candidates = self._search.candidates(year, department, grades)
        profile = self._analyzer.analyze(occupation)
        [matches] = candidates.rank([profile.query], self._candidate_limit)
        if not matches:
            return Recommendation(profile, (), ())
        codes = {match.syllabus_code for match in matches}
        pages = self._courses.syllabi_of(year, codes)
        missing = sorted(codes - pages.keys())
        if missing:
            raise RecommendationError(f"シラバスが DB にありません: {'、'.join(missing)}")
        offered = [CandidateCourse(match.name, pages[match.syllabus_code]) for match in matches]
        return arrange(profile, matches, self._selector.select(profile, offered))
