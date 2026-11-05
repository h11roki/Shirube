import logging
from collections.abc import Callable, Sequence, Set
from datetime import datetime, timedelta

from app.application.ports import CourseRepository, RecommendationKey, RecommendationStore
from app.application.recommend_courses import Recommender, RecommendStep
from app.domain.course import left_out_codes
from app.domain.recommendation import Recommendation
from app.domain.roadmap import Semester, opens_in_any

logger = logging.getLogger(__name__)


class CachedRecommender:
    def __init__(
        self,
        recommender: Recommender,
        store: RecommendationStore,
        courses: CourseRepository,
        fingerprint: str,
        lifetime: timedelta,
        now: Callable[[], datetime],
    ) -> None:
        if lifetime <= timedelta(0):
            raise ValueError(f"推薦を残す期間は正にしてください: {lifetime}")
        self._recommender = recommender
        self._store = store
        self._courses = courses
        self._fingerprint = fingerprint
        self._lifetime = lifetime
        self._now = now

    def run(
        self,
        occupation: str,
        year: int,
        department: str,
        semesters: Sequence[Semester],
        enter: Callable[[RecommendStep], None] = lambda step: None,
        excluded: Set[str] = frozenset(),
    ) -> Recommendation:
        key = RecommendationKey(
            occupation,
            department,
            year,
            tuple(semesters),
            self._left_out(year, department, semesters, excluded),
            self._fingerprint,
        )
        now = self._now()
        try:
            remembered = self._store.recall(key, now)
        except Exception:
            logger.exception("残した推薦を読めなかったので、推薦を作り直します: %s", key.digest[:8])
            remembered = None
        if remembered is not None:
            logger.info("残した推薦を使います: %s", key.digest[:8])
            return remembered
        logger.info("残した推薦が無いので作ります: %s", key.digest[:8])
        recommendation = self._recommender.run(
            occupation, year, department, semesters, enter, excluded
        )
        try:
            self._store.remember(key, recommendation, now + self._lifetime)
        except Exception:
            logger.exception("推薦を残せませんでしたが、道標はそのまま作ります: %s", key.digest[:8])
        return recommendation

    def _left_out(
        self, year: int, department: str, semesters: Sequence[Semester], excluded: Set[str]
    ) -> tuple[str, ...]:
        if not excluded:
            return ()
        sections = self._courses.sections(year)
        page_of = self._courses.syllabus_codes(year)
        left_out = left_out_codes(sections, page_of, department, excluded)
        return tuple(
            sorted(
                section.code
                for section in sections
                if section.code in left_out
                and section.code in page_of
                and opens_in_any(section, department, year, semesters)
            )
        )
