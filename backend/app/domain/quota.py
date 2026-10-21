from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.course import UNIVERSITY_TIME

IN_PROGRESS_LIMIT = 1
REOPENS = "明日の 0 時(日本時間)からまた作れます"


class PlanRefusedError(ValueError):
    pass


class PlanInProgressError(PlanRefusedError):
    pass


class DailyLimitError(PlanRefusedError):
    def __init__(self, message: str, retry_after: timedelta) -> None:
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class PlanCounts:
    in_progress: int
    owner_today: int
    all_today: int


@dataclass(frozen=True)
class PlanQuota:
    per_user: int
    total: int

    def admit(self, counts: PlanCounts, now: datetime) -> None:
        if counts.in_progress >= IN_PROGRESS_LIMIT:
            raise PlanInProgressError("作っている道標ができてから、次の道標を作れます")
        retry_after = day_start(now) + timedelta(days=1) - now
        if counts.owner_today >= self.per_user:
            raise DailyLimitError(
                f"道標を作れるのは 1 人 1 日 {self.per_user} 件までです。{REOPENS}", retry_after
            )
        if counts.all_today >= self.total:
            raise DailyLimitError(
                f"今日は全体で作れる {self.total} 件に達しました。{REOPENS}", retry_after
            )


def day_start(moment: datetime) -> datetime:
    return moment.astimezone(UNIVERSITY_TIME).replace(hour=0, minute=0, second=0, microsecond=0)
