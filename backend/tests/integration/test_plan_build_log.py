from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, func, select, update
from sqlalchemy.exc import IntegrityError

from app.application.ports import BuildOutcome, FailureCause, PlanBuild, TokenUsage
from app.domain.plan import Plan, PlanStage
from app.domain.quota import PlanCounts
from app.infrastructure.db.models import PlanBuildRow, PlanRow, UserRow
from app.infrastructure.db.plan_builds import SqlPlanBuildLog
from app.infrastructure.db.plans import SqlPlanRepository
from app.infrastructure.db.users import SqlUserRepository
from tests.builders import sample_conditions

ANY_DAY = datetime(2000, 1, 1, tzinfo=UTC)
QUEUED = timedelta(seconds=90)
OUT_OF_CREDIT = PlanBuild(
    BuildOutcome.FAILED,
    FailureCause(("CourseSelectionError", "RateLimitError"), "insufficient_quota"),
    {PlanStage.ANALYZING: 1.5, PlanStage.SEARCHING: 0.25, PlanStage.SELECTING: 12.0},
    {"gpt-5.4-mini": TokenUsage(300, 100, 50), "gpt-5.4-nano": TokenUsage(9000, 6000, 700)},
)


def allow(counts: PlanCounts) -> None:
    pass


@pytest.fixture
def log(engine: Engine) -> Iterator[SqlPlanBuildLog]:
    yield SqlPlanBuildLog(engine)
    with engine.begin() as connection:
        connection.execute(delete(PlanBuildRow))
        connection.execute(delete(PlanRow))
        connection.execute(delete(UserRow))


def claimed(engine: Engine) -> Plan:
    plans = SqlPlanRepository(engine)
    plan = Plan(uuid4(), SqlUserRepository(engine).id_of("google-a"), sample_conditions())
    plans.add(plan, ANY_DAY, allow)
    with engine.begin() as connection:
        connection.execute(
            update(PlanRow).where(PlanRow.id == plan.id).values(created_at=func.now() - QUEUED)
        )
    plans.claim(plan.id)
    return plan


def test_a_recorded_build_comes_back_with_how_long_its_plan_waited(
    engine: Engine, log: SqlPlanBuildLog
) -> None:
    plan = claimed(engine)

    log.record(plan.id, OUT_OF_CREDIT)

    [recorded] = log.since(ANY_DAY)
    assert recorded.build == OUT_OF_CREDIT
    assert recorded.queued_seconds == pytest.approx(QUEUED.total_seconds(), abs=5)


def test_a_record_outlives_its_plan_and_its_owner(engine: Engine, log: SqlPlanBuildLog) -> None:
    plan = claimed(engine)
    log.record(plan.id, PlanBuild(BuildOutcome.SUCCEEDED))

    with engine.begin() as connection:
        connection.execute(delete(UserRow))

    assert [recorded.build for recorded in log.since(ANY_DAY)] == [
        PlanBuild(BuildOutcome.SUCCEEDED)
    ]
    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(PlanRow)) == 0


def test_a_build_of_a_plan_that_is_gone_has_no_waiting_time(log: SqlPlanBuildLog) -> None:
    log.record(uuid4(), PlanBuild(BuildOutcome.STALLED))

    [recorded] = log.since(ANY_DAY)
    assert (recorded.build, recorded.queued_seconds) == (PlanBuild(BuildOutcome.STALLED), None)


def test_only_builds_finished_since_the_start_come_back_oldest_first(
    engine: Engine, log: SqlPlanBuildLog
) -> None:
    for outcome in (BuildOutcome.SUCCEEDED, BuildOutcome.DISCARDED, BuildOutcome.STALLED):
        log.record(uuid4(), PlanBuild(outcome))
    with engine.begin() as connection:
        connection.execute(
            update(PlanBuildRow)
            .where(PlanBuildRow.outcome == BuildOutcome.SUCCEEDED.value)
            .values(finished_at=func.now() - timedelta(days=2))
        )
        connection.execute(
            update(PlanBuildRow)
            .where(PlanBuildRow.outcome == BuildOutcome.STALLED.value)
            .values(finished_at=func.now() - timedelta(hours=1))
        )

    recent = log.since(datetime.now(UTC) - timedelta(days=1))

    assert [recorded.build.outcome for recorded in recent] == [
        BuildOutcome.STALLED,
        BuildOutcome.DISCARDED,
    ]


def test_a_failed_build_must_say_what_caused_it(log: SqlPlanBuildLog) -> None:
    with pytest.raises(IntegrityError):
        log.record(uuid4(), PlanBuild(BuildOutcome.FAILED))
