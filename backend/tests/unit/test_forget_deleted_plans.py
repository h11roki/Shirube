from datetime import datetime
from uuid import uuid4

import pytest

from app.application.forget_deleted_plans import ForgetDeletedPlans
from tests.builders import sample_plan
from tests.fakes import FakePlanRepository


class Clock:
    def __init__(self, moment: str) -> None:
        self.now = datetime.fromisoformat(moment)

    def __call__(self) -> datetime:
        return self.now

    def move_to(self, moment: str) -> None:
        self.now = datetime.fromisoformat(moment)


class FailingOnce(FakePlanRepository):
    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    def purge_deleted(self, before: datetime) -> int:
        if not self.failed:
            self.failed = True
            raise ConnectionError("DB に届きません")
        return super().purge_deleted(before)


def test_times_of_plans_made_before_today_in_japan_are_forgotten_once_a_day() -> None:
    plans = FakePlanRepository()
    yesterday, today = sample_plan(uuid4()), sample_plan(uuid4())
    plans.created_at[yesterday.id] = datetime.fromisoformat("2026-10-20T23:59+09:00")
    plans.created_at[today.id] = datetime.fromisoformat("2026-10-21T00:00+09:00")
    plans.deleted = {yesterday.id: None, today.id: None}
    clock = Clock("2026-10-21T09:00+09:00")
    forgetting = ForgetDeletedPlans(plans, clock)

    forgetting.run()
    clock.move_to("2026-10-21T23:59+09:00")
    forgetting.run()
    clock.move_to("2026-10-22T00:01+09:00")
    forgetting.run()

    assert list(plans.deleted) == []
    assert plans.purges == [
        datetime.fromisoformat("2026-10-21T00:00+09:00"),
        datetime.fromisoformat("2026-10-22T00:00+09:00"),
    ]


def test_a_failed_purge_is_tried_again_ten_minutes_later() -> None:
    plans = FailingOnce()
    clock = Clock("2026-10-21T00:01+09:00")
    forgetting = ForgetDeletedPlans(plans, clock)

    with pytest.raises(ConnectionError):
        forgetting.run()
    clock.move_to("2026-10-21T00:10+09:00")
    forgetting.run()
    clock.move_to("2026-10-21T00:11+09:00")
    forgetting.run()

    assert plans.purges == [datetime.fromisoformat("2026-10-21T00:00+09:00")]
