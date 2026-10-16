from collections.abc import Set

from app.application.ports import CourseRepository, CourseSelector, OccupationAnalyzer
from app.application.search_courses import SearchCourses
from app.domain.recommendation import (
    RELEVANCE_ORDER,
    CandidateCourse,
    Recommendation,
    RecommendationError,
    RecommendedCourse,
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
        offered = []
        for match in matches:
            page = self._courses.syllabus(year, match.syllabus_code)
            if page is None:
                message = f"{match.name}: シラバス {match.syllabus_code} が DB にありません"
                raise RecommendationError(message)
            offered.append(CandidateCourse(match.name, page))
        if not offered:
            return Recommendation(profile, (), 0)
        choices = self._selector.select(profile, offered)
        rank_of = {match.name: rank for rank, match in enumerate(matches)}
        unknown = sorted({choice.name for choice in choices} - rank_of.keys())
        if unknown:
            raise RecommendationError(f"候補に無い科目が選ばれています: {'、'.join(unknown)}")
        code_of = {match.name: match.syllabus_code for match in matches}
        ordered = sorted(
            choices,
            key=lambda choice: (RELEVANCE_ORDER.index(choice.relevance), rank_of[choice.name]),
        )
        courses = tuple(
            RecommendedCourse(choice.name, code_of[choice.name], choice.relevance, choice.reason)
            for choice in ordered
        )
        return Recommendation(profile, courses, len(offered))
