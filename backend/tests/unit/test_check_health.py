from datetime import timedelta

import pytest

from app.application.check_health import Health
from app.application.ports import (
    OUT_OF_CREDIT,
    BuildOutcome,
    FailureCause,
    PlanBuild,
    RecordedBuild,
    TokenUsage,
)
from app.domain.plan import PlanStatus
from tests.fakes import (
    FIRST_CREATED_AT,
    QUEUE_STALL_AFTER,
    FakePlanRepository,
    UnreachablePlans,
    health_of,
    queued,
)

NO_CREDIT = FailureCause(("OccupationAnalysisError", "RateLimitError"), OUT_OF_CREDIT)
TIMEOUT = FailureCause(("CourseSelectionError", "APITimeoutError"))
CALLED = {"gpt-5.4-nano": TokenUsage(100, 0, 10)}


def finished(
    hours_ago: float,
    outcome: BuildOutcome,
    cause: FailureCause | None = None,
    usage: dict[str, TokenUsage] | None = None,
) -> RecordedBuild:
    return RecordedBuild(
        FIRST_CREATED_AT - timedelta(hours=hours_ago),
        1.0,
        PlanBuild(outcome, cause, usage=usage if usage is not None else CALLED),
    )


def test_a_quiet_service_is_healthy() -> None:
    assert health_of(FakePlanRepository()).run() == Health(True, False, False)


@pytest.mark.parametrize(
    ("waited", "stalled"),
    [(QUEUE_STALL_AFTER, False), (QUEUE_STALL_AFTER + timedelta(seconds=1), True)],
    ids=["within-the-limit", "past-the-limit"],
)
def test_the_queue_stalls_when_a_plan_waits_past_the_limit(
    waited: timedelta, stalled: bool
) -> None:
    assert health_of(queued(waited)).run().queue_stalled is stalled


def test_plans_being_built_do_not_count_as_waiting() -> None:
    assert health_of(queued(timedelta(days=1), PlanStatus.RUNNING)).run().queue_stalled is False


@pytest.mark.parametrize(
    ("builds", "out_of_credit"),
    [
        ([finished(2, BuildOutcome.FAILED, NO_CREDIT, {})], True),
        (
            [finished(3, BuildOutcome.FAILED, NO_CREDIT, {}), finished(1, BuildOutcome.SUCCEEDED)],
            False,
        ),
        ([finished(1, BuildOutcome.FAILED, TIMEOUT)], False),
        ([finished(25, BuildOutcome.FAILED, NO_CREDIT, {})], False),
        (
            [
                finished(3, BuildOutcome.FAILED, NO_CREDIT, {}),
                finished(2, BuildOutcome.SUCCEEDED, usage={}),
                finished(1, BuildOutcome.STALLED, usage={}),
            ],
            True,
        ),
    ],
    ids=[
        "last-call-out-of-credit",
        "succeeded-after-topping-up",
        "other-failure",
        "a-day-ago",
        "builds-without-openai-calls-do-not-clear-it",
    ],
)
def test_credit_is_out_when_the_last_build_that_called_openai_failed_for_it(
    builds: list[RecordedBuild], out_of_credit: bool
) -> None:
    assert health_of(FakePlanRepository(), builds).run().out_of_credit is out_of_credit


def test_an_unreachable_database_is_reported_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    assert health_of(UnreachablePlans()).run() == Health(database_reachable=False)
    assert "health: DB を読めませんでした" in caplog.text
    assert "DB に繋がらない" in caplog.text
