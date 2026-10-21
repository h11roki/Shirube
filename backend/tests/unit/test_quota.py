from datetime import UTC, datetime, timedelta

import pytest

from app.domain.quota import (
    DailyLimitError,
    PlanCounts,
    PlanInProgressError,
    PlanQuota,
    day_start,
)
from app.domain.roadmap import UNIVERSITY_TIME

QUOTA = PlanQuota(per_user=3, total=30)
EVENING = datetime(2026, 10, 21, 10, 30, tzinfo=UTC)


def test_the_day_starts_at_midnight_in_japan() -> None:
    assert day_start(datetime(2026, 10, 21, 14, 59, 59, tzinfo=UTC)) == datetime(
        2026, 10, 21, tzinfo=UNIVERSITY_TIME
    )
    assert day_start(datetime(2026, 10, 21, 15, 0, tzinfo=UTC)) == datetime(
        2026, 10, 22, tzinfo=UNIVERSITY_TIME
    )


def test_a_plan_is_admitted_below_every_limit() -> None:
    QUOTA.admit(PlanCounts(in_progress=0, owner_today=2, all_today=29), EVENING)


def test_a_plan_in_progress_is_refused_before_the_daily_limits() -> None:
    with pytest.raises(PlanInProgressError, match="作っている道標ができてから"):
        QUOTA.admit(PlanCounts(in_progress=1, owner_today=3, all_today=30), EVENING)


def test_the_users_daily_limit_is_refused_until_midnight_in_japan() -> None:
    with pytest.raises(DailyLimitError, match="1 人 1 日 3 件まで") as refused:
        QUOTA.admit(PlanCounts(in_progress=0, owner_today=3, all_today=3), EVENING)

    assert refused.value.retry_after == timedelta(hours=4, minutes=30)


def test_the_total_daily_limit_is_refused_even_for_a_new_user() -> None:
    with pytest.raises(DailyLimitError, match="全体で作れる 30 件に達しました"):
        QUOTA.admit(PlanCounts(in_progress=0, owner_today=0, all_today=30), EVENING)
