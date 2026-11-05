import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from app.application.ports import PlanRepository, RecommendationStore
from app.domain.quota import day_start

RETRY_AFTER = timedelta(minutes=10)

logger = logging.getLogger(__name__)


class TidyDaily:
    def __init__(
        self,
        plans: PlanRepository,
        recommendations: RecommendationStore,
        now: Callable[[], datetime],
    ) -> None:
        self._plans = plans
        self._recommendations = recommendations
        self._now = now
        self._tidied_before: datetime | None = None
        self._retry_at: datetime | None = None

    def run(self) -> None:
        now = self._now()
        before = day_start(now)
        if before == self._tidied_before or (self._retry_at is not None and now < self._retry_at):
            return
        self._retry_at = now + RETRY_AFTER
        purged = self._plans.purge_deleted(before)
        forgotten = self._recommendations.forget_expired(now)
        self._tidied_before = before
        self._retry_at = None
        if purged:
            logger.info("前の日までに消した道標 %d 件の日時を消しました", purged)
        if forgotten:
            logger.info("期限の切れた推薦 %d 件を消しました", forgotten)
