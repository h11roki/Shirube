from collections.abc import Set

from app.application.ports import CourseRepository, CourseSelector, OccupationAnalyzer
from app.application.search_courses import SearchCourses
from app.domain.recommendation import (
    CandidateCourse,
    Recommendation,
    RecommendationError,
    RecommendedCourse,
    Relevance,
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
            return Recommendation(profile, (), 0)
        pages = self._courses.syllabi_of(year, {match.syllabus_code for match in matches})
        missing = sorted({match.syllabus_code for match in matches} - pages.keys())
        if missing:
            raise RecommendationError(f"シラバスが DB にありません: {'、'.join(missing)}")
        offered = [CandidateCourse(match.name, pages[match.syllabus_code]) for match in matches]
        choices = self._selector.select(profile, offered)
        ranked = {match.name: (rank, match) for rank, match in enumerate(matches)}
        unknown = sorted({choice.name for choice in choices} - ranked.keys())
        if unknown:
            raise RecommendationError(f"候補に無い科目が選ばれています: {'、'.join(unknown)}")
        relevance_order = list(Relevance)
        ordered = sorted(
            choices,
            key=lambda choice: (
                relevance_order.index(choice.relevance),
                ranked[choice.name][0],
            ),
        )
        courses = tuple(
            RecommendedCourse(
                choice.name, ranked[choice.name][1].syllabus_code, choice.relevance, choice.reason
            )
            for choice in ordered
        )
        return Recommendation(profile, courses, len(offered))
