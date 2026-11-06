from datetime import datetime, timedelta
from uuid import uuid4

from app.application.ports import (
    OUT_OF_CREDIT,
    BuildOutcome,
    FailureCause,
    PlanBuild,
    RecordedBuild,
)
from app.domain.plan import Plan
from tests.builders import sample_conditions
from tests.fakes import API_VERSION, FIRST_CREATED_AT, FakePlanRepository, health_of, plan_api


class UnreachablePlans(FakePlanRepository):
    def oldest_waiting(self) -> datetime | None:
        raise ConnectionError("DB に繋がらない")


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
    plans = FakePlanRepository()
    plan = Plan(uuid4(), uuid4(), sample_conditions())
    plans.store(plan)
    plans.created_at[plan.id] = FIRST_CREATED_AT - timedelta(hours=1)
    out_of_credit = RecordedBuild(
        FIRST_CREATED_AT,
        1.0,
        PlanBuild(BuildOutcome.FAILED, FailureCause(("RateLimitError",), OUT_OF_CREDIT)),
    )

    response = plan_api(token=None, health=health_of(plans, [out_of_credit])).get("/api/v1/health")

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
