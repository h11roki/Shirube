from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.application.check_health import Health
from app.application.ports import (
    OUT_OF_CREDIT,
    BuildOutcome,
    FailureCause,
    PlanBuild,
    RecordedBuild,
)
from app.domain.plan import Plan, PlanStatus
from tests.builders import sample_conditions
from tests.fakes import FIRST_CREATED_AT, FakePlanRepository, health_of

NO_CREDIT = FailureCause(("OccupationAnalysisError", "RateLimitError"), OUT_OF_CREDIT)
TIMEOUT = FailureCause(("CourseSelectionError", "APITimeoutError"))


def queued(minutes_ago: float, status: PlanStatus = PlanStatus.PENDING) -> FakePlanRepository:
    plans = FakePlanRepository()
    plan = replace(Plan(uuid4(), uuid4(), sample_conditions()), status=status)
    plans.store(plan)
    plans.created_at[plan.id] = FIRST_CREATED_AT - timedelta(minutes=minutes_ago)
    return plans


def finished(
    hours_ago: float, outcome: BuildOutcome, cause: FailureCause | None = None
) -> RecordedBuild:
    return RecordedBuild(
        FIRST_CREATED_AT - timedelta(hours=hours_ago), 1.0, PlanBuild(outcome, cause)
    )


class UnreachablePlans(FakePlanRepository):
    def oldest_waiting(self) -> datetime | None:
        raise ConnectionError("DB に繋がらない")


def test_a_quiet_service_is_healthy() -> None:
    assert health_of(FakePlanRepository()).run() == Health(True, False, False)


@pytest.mark.parametrize(
    ("minutes_ago", "stalled"),
    [(20, False), (20.5, True)],
    ids=["within-the-stall-limit", "past-the-stall-limit"],
)
def test_the_queue_stalls_when_a_plan_waits_past_the_stall_limit(
    minutes_ago: float, stalled: bool
) -> None:
    assert health_of(queued(minutes_ago)).run().queue_stalled is stalled


def test_plans_being_built_do_not_count_as_waiting() -> None:
    assert health_of(queued(60, PlanStatus.RUNNING)).run().queue_stalled is False


@pytest.mark.parametrize(
    ("builds", "out_of_credit"),
    [
        ([finished(2, BuildOutcome.FAILED, NO_CREDIT)], True),
        (
            [finished(3, BuildOutcome.FAILED, NO_CREDIT), finished(1, BuildOutcome.SUCCEEDED)],
            False,
        ),
        ([finished(1, BuildOutcome.FAILED, TIMEOUT)], False),
        ([finished(25, BuildOutcome.FAILED, NO_CREDIT)], False),
    ],
    ids=["last-build-out-of-credit", "succeeded-after-topping-up", "other-failure", "a-day-ago"],
)
def test_credit_runs_out_when_the_last_build_of_the_day_failed_for_it(
    builds: list[RecordedBuild], out_of_credit: bool
) -> None:
    assert health_of(FakePlanRepository(), builds).run().out_of_credit is out_of_credit


def test_an_unreachable_database_is_reported_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    assert health_of(UnreachablePlans()).run() == Health(database_reachable=False)
    assert "health: DB を読めませんでした" in caplog.text
    assert "DB に繋がらない" in caplog.text
