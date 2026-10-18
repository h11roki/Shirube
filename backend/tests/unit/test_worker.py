import logging
import threading
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import OperationalError

from app.application.build_plans import BuildPlans
from app.application.ports import PlanFormatError
from app.application.recommend_courses import RecommendCourses
from app.domain.course import Term
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan, PlanConditions, PlanStatus
from app.domain.roadmap import Semester
from app.presentation.worker import work
from tests.fakes import (
    FakeCourseSelector,
    FakeOccupationAnalyzer,
    FakePlanRepository,
    courses_ranked_by,
)

PROFILE = OccupationProfile("職業", "解釈した職業", None, ("甲", "乙", "丙"))
STALL_LIMIT = timedelta(minutes=15)


class StopWhenIdle(FakePlanRepository):
    def __init__(
        self, stop: threading.Event, failing_calls: int = 0, unreadable_claims: int = 0
    ) -> None:
        super().__init__()
        self._stop = stop
        self._failing_calls = failing_calls
        self._unreadable_claims = unreadable_claims

    def fail_stalled(self, after: timedelta, failure: str) -> list[UUID]:
        if self._failing_calls:
            self._failing_calls -= 1
            raise OperationalError("SELECT 1", {}, Exception("接続が切れました"))
        return super().fail_stalled(after, failure)

    def claim_next(self) -> Plan | None:
        if self._unreadable_claims:
            self._unreadable_claims -= 1
            raise PlanFormatError("読めない道標です")
        claimed = super().claim_next()
        if claimed is None:
            self._stop.set()
        return claimed


def builder(plans: FakePlanRepository) -> BuildPlans:
    courses, search = courses_ranked_by({"科目A": 0.9})
    recommend = RecommendCourses(
        search, courses, FakeOccupationAnalyzer({"職業": PROFILE}), FakeCourseSelector([]), 30
    )
    return BuildPlans(recommend, courses, plans)


def waiting(plans: FakePlanRepository) -> Plan:
    conditions = PlanConditions("職業", "情", 2026, Semester(3, Term.SPRING), (), 16)
    plan = Plan(uuid4(), uuid4(), conditions)
    plans.add(plan)
    return plan


def test_the_worker_builds_every_waiting_plan_until_it_is_told_to_stop() -> None:
    stop = threading.Event()
    plans = StopWhenIdle(stop)
    first, second = waiting(plans), waiting(plans)

    work(builder(plans), STALL_LIMIT, 0.01, stop)

    assert [plans.plans[plan.id].status for plan in (first, second)] == [
        PlanStatus.SUCCEEDED,
        PlanStatus.SUCCEEDED,
    ]
    assert plans.stall_limits == [STALL_LIMIT] * 3


def test_the_worker_logs_a_failed_round_and_tries_again(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stop = threading.Event()
    plans = StopWhenIdle(stop, failing_calls=1)
    plan = waiting(plans)

    with caplog.at_level(logging.ERROR):
        work(builder(plans), STALL_LIMIT, 0.01, stop)

    assert plans.plans[plan.id].status is PlanStatus.SUCCEEDED
    assert "道標の worker の繰り返しに失敗しました" in caplog.text


def test_the_worker_does_not_start_once_it_is_told_to_stop() -> None:
    stop = threading.Event()
    stop.set()
    plans = StopWhenIdle(stop)
    plan = waiting(plans)

    work(builder(plans), STALL_LIMIT, 0.01, stop)

    assert plans.plans[plan.id].status is PlanStatus.PENDING


def test_the_worker_logs_a_plan_it_cannot_read_and_goes_on(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stop = threading.Event()
    plans = StopWhenIdle(stop, unreadable_claims=1)
    plan = waiting(plans)

    with caplog.at_level(logging.ERROR):
        work(builder(plans), STALL_LIMIT, 0.01, stop)

    assert plans.plans[plan.id].status is PlanStatus.SUCCEEDED
    assert "取った道標を読めない" in caplog.text


def test_the_worker_takes_no_new_plan_once_told_to_stop_while_failing_stalled_plans() -> None:
    stop = threading.Event()

    class StopWhileFailingStalled(StopWhenIdle):
        def fail_stalled(self, after: timedelta, failure: str) -> list[UUID]:
            stop.set()
            return super().fail_stalled(after, failure)

    plans = StopWhileFailingStalled(stop)
    plan = waiting(plans)

    work(builder(plans), STALL_LIMIT, 0.01, stop)

    assert plans.plans[plan.id].status is PlanStatus.PENDING
