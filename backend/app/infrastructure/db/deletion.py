from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, case, insert, null, select
from sqlalchemy.orm import Session

from app.domain.plan import PlanStatus
from app.infrastructure.db.models import DeletedPlanRow, PlanRow

ADMISSION_LOCK = 380038
COUNTED_OWNER = case((PlanRow.status == PlanStatus.FAILED, null()), else_=PlanRow.user_id)


def keep_deleted_times(
    db: Session, which: ColumnElement[bool], since: datetime, owner: ColumnElement[Any]
) -> None:
    db.execute(
        insert(DeletedPlanRow).from_select(
            ["id", "user_id", "created_at"],
            select(PlanRow.id, owner, PlanRow.created_at).where(which, PlanRow.created_at >= since),
        )
    )
