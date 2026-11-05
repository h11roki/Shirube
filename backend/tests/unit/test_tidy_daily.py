from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.application.ports import RecommendationKey
from app.application.tidy_daily import TidyDaily
from app.domain.course import Term
from app.domain.roadmap import Semester
from tests.builders import sample_plan
from tests.fakes import FakePlanRepository, FakeRecommendationStore


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


class ForgettingFailsOnce(FakeRecommendationStore):
    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    def forget_expired(self, now: datetime) -> int:
        if not self.failed:
            self.failed = True
            raise ConnectionError("DB に届きません")
        return super().forget_expired(now)


def remembered_until(store: FakeRecommendationStore, name: str, until: str) -> None:
    key = RecommendationKey(name, "情", 2026, (Semester(3, Term.SPRING),), (), "f1")
    recommendation = sample_plan(uuid4()).result
    assert recommendation is not None
    store.remember(key, recommendation.recommendation, datetime.fromisoformat(until))


def test_times_of_plans_made_before_today_in_japan_are_forgotten_once_a_day() -> None:
    plans = FakePlanRepository()
    yesterday, today = sample_plan(uuid4()), sample_plan(uuid4())
    plans.created_at[yesterday.id] = datetime.fromisoformat("2026-10-20T23:59+09:00")
    plans.created_at[today.id] = datetime.fromisoformat("2026-10-21T00:00+09:00")
    plans.deleted = {yesterday.id: None, today.id: None}
    clock = Clock("2026-10-21T09:00+09:00")
    tidying = TidyDaily(plans, FakeRecommendationStore(), clock)

    tidying.run()
    clock.move_to("2026-10-21T23:59+09:00")
    tidying.run()
    clock.move_to("2026-10-22T00:01+09:00")
    tidying.run()

    assert list(plans.deleted) == []
    assert plans.purges == [
        datetime.fromisoformat("2026-10-21T00:00+09:00"),
        datetime.fromisoformat("2026-10-22T00:00+09:00"),
    ]


def test_expired_recommendations_are_forgotten_with_the_same_daily_tidying() -> None:
    store = FakeRecommendationStore()
    remembered_until(store, "職業A", "2026-10-21T08:00+09:00")
    remembered_until(store, "職業B", "2026-10-21T10:00+09:00")
    clock = Clock("2026-10-21T09:00+09:00")
    tidying = TidyDaily(FakePlanRepository(), store, clock)

    tidying.run()
    clock.move_to("2026-10-21T11:00+09:00")
    tidying.run()

    assert store.forgets == [datetime.fromisoformat("2026-10-21T09:00+09:00")]
    assert [key.occupation for key, _, _ in store.remembered.values()] == ["職業B"]


def test_a_failed_purge_is_tried_again_ten_minutes_later() -> None:
    plans = FailingOnce()
    clock = Clock("2026-10-21T00:01+09:00")
    tidying = TidyDaily(plans, FakeRecommendationStore(), clock)

    with pytest.raises(ConnectionError):
        tidying.run()
    clock.move_to("2026-10-21T00:10+09:00")
    tidying.run()
    clock.move_to("2026-10-21T00:11+09:00")
    tidying.run()

    assert plans.purges == [datetime.fromisoformat("2026-10-21T00:00+09:00")]


def test_a_failed_forgetting_of_recommendations_repeats_both_purges_ten_minutes_later() -> None:
    plans = FakePlanRepository()
    store = ForgettingFailsOnce()
    clock = Clock("2026-10-21T00:01+09:00")
    tidying = TidyDaily(plans, store, clock)

    with pytest.raises(ConnectionError):
        tidying.run()
    clock.move_to(str(clock.now + timedelta(minutes=10)))
    tidying.run()

    assert plans.purges == [datetime.fromisoformat("2026-10-21T00:00+09:00")] * 2
    assert store.forgets == [datetime.fromisoformat("2026-10-21T00:11+09:00")]
