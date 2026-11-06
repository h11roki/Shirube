from datetime import datetime, timedelta

import pytest

from app.application.ports import (
    OUT_OF_CREDIT,
    BuildOutcome,
    FailureCause,
    PlanBuild,
    RecordedBuild,
)
from tests.fakes import (
    API_VERSION,
    FIRST_CREATED_AT,
    STALL_AFTER,
    FakePlanRepository,
    UnreachablePlans,
    health_of,
    plan_api,
    queued,
)


class BrokenPlans(FakePlanRepository):
    def oldest_waiting(self) -> datetime | None:
        raise ValueError("読めない値")


def test_health_reports_every_check_and_the_version_without_a_login() -> None:
    response = plan_api(token=None).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": API_VERSION,
        "database": "ok",
        "queue": "ok",
        "openai": "ok",
    }


def test_a_stalled_queue_and_no_credit_degrade_the_service_but_it_still_answers() -> None:
    out_of_credit = RecordedBuild(
        FIRST_CREATED_AT,
        1.0,
        PlanBuild(BuildOutcome.FAILED, FailureCause(("RateLimitError",), OUT_OF_CREDIT)),
    )
    stalled = queued(STALL_AFTER + timedelta(minutes=1))

    response = plan_api(token=None, health=health_of(stalled, [out_of_credit])).get(
        "/api/v1/health"
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "version": API_VERSION,
        "database": "ok",
        "queue": "stalled",
        "openai": "out_of_credit",
    }


def test_an_unreachable_database_is_a_logged_503_with_the_other_checks_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    response = plan_api(token=None, health=health_of(UnreachablePlans())).get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "down",
        "version": API_VERSION,
        "database": "down",
        "queue": "unknown",
        "openai": "unknown",
    }
    assert "health: DB に繋がりませんでした" in caplog.text
    assert "DB に繋がらない" in caplog.text


def test_other_errors_are_a_server_failure_rather_than_an_unreachable_database() -> None:
    response = plan_api(token=None, health=health_of(BrokenPlans())).get("/api/v1/health")

    assert response.status_code == 500
