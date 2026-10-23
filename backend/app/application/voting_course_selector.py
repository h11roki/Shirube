from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

from app.application.ports import CourseSelector
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse, CourseChoice, majority_choices


class VotingCourseSelector:
    def __init__(self, selector: CourseSelector, votes: int) -> None:
        self._selector = selector
        self._votes = votes

    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        with ThreadPoolExecutor(max_workers=self._votes) as pool:
            futures = [
                pool.submit(copy_context().run, self._selector.select, profile, candidates)
                for _ in range(self._votes)
            ]
            samples = [future.result() for future in futures]
        return majority_choices(samples)
