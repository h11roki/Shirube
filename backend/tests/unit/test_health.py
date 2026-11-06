from datetime import timedelta

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
    QUEUE_STALL_AFTER,
    UnreachablePlans,
    health_of,
    plan_api,
    queued,
)


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
    stalled = queued(QUEUE_STALL_AFTER + timedelta(minutes=1))

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


def test_an_unreachable_database_is_a_503_with_the_other_checks_unknown() -> None:
    response = plan_api(token=None, health=health_of(UnreachablePlans())).get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "down",
        "version": API_VERSION,
        "database": "down",
        "queue": "unknown",
        "openai": "unknown",
    }
