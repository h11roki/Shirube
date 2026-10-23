import logging
from contextvars import Context, copy_context
from threading import Thread

from app.application.ports import CourseSelector
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse, CourseChoice, majority_choices

logger = logging.getLogger(__name__)


class VotingCourseSelector:
    def __init__(self, selector: CourseSelector, votes: int) -> None:
        self._selector = selector
        self._votes = votes

    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        answers: list[list[CourseChoice] | Exception] = [[] for _ in range(self._votes)]

        def vote(index: int, context: Context) -> None:
            try:
                answers[index] = context.run(self._selector.select, profile, candidates)
            except Exception as error:
                answers[index] = error

        threads = [
            Thread(target=vote, args=(index, copy_context()), daemon=True)
            for index in range(self._votes)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        failures = [answer for answer in answers if isinstance(answer, Exception)]
        for failure in failures[1:]:
            logger.warning("選び直しのほかの票も失敗しました: %r", failure)
        if failures:
            raise failures[0]
        return majority_choices([answer for answer in answers if not isinstance(answer, Exception)])
