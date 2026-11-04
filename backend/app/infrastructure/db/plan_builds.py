from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import Engine, func, insert, select
from sqlalchemy.orm import Session as DbSession

from app.application.ports import (
    BuildOutcome,
    FailureCause,
    PlanBuild,
    RecordedBuild,
    TokenUsage,
)
from app.domain.plan import PlanStage
from app.infrastructure.db.models import PlanBuildRow, PlanRow


class SqlPlanBuildLog:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record(self, plan_id: UUID, build: PlanBuild) -> None:
        queued = (
            select(func.extract("epoch", PlanRow.claimed_at - PlanRow.created_at))
            .where(PlanRow.id == plan_id)
            .scalar_subquery()
        )
        with DbSession(self._engine) as db, db.begin():
            db.execute(
                insert(PlanBuildRow).values(
                    outcome=build.outcome.value,
                    cause_types=[] if build.cause is None else list(build.cause.types),
                    cause_code=None if build.cause is None else build.cause.code,
                    queued_seconds=queued,
                    seconds={stage.value: seconds for stage, seconds in build.seconds.items()},
                    usage={model: asdict(tokens) for model, tokens in build.usage.items()},
                )
            )

    def since(self, start: datetime) -> list[RecordedBuild]:
        with DbSession(self._engine) as db:
            rows = db.scalars(
                select(PlanBuildRow)
                .where(PlanBuildRow.finished_at >= start)
                .order_by(PlanBuildRow.finished_at, PlanBuildRow.id)
            )
            return [
                RecordedBuild(
                    row.finished_at,
                    row.queued_seconds,
                    PlanBuild(
                        BuildOutcome(row.outcome),
                        FailureCause(tuple(row.cause_types), row.cause_code)
                        if row.cause_types
                        else None,
                        {PlanStage(stage): seconds for stage, seconds in row.seconds.items()},
                        {model: TokenUsage(**tokens) for model, tokens in row.usage.items()},
                    ),
                )
                for row in rows
            ]
