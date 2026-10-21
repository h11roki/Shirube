from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.application.ports import Deletion, PlanRepository, PlanRunningError
from app.domain.quota import day_start


class DeletePlan:
    def __init__(self, plans: PlanRepository, now: Callable[[], datetime]) -> None:
        self._plans = plans
        self._now = now

    def run(self, *, owner_id: UUID, plan_id: UUID) -> bool:
        deletion = self._plans.delete_owned_by(plan_id, owner_id, day_start(self._now()))
        if deletion is Deletion.RUNNING:
            raise PlanRunningError("作っている途中の道標は、できてから消せます")
        return deletion is Deletion.DELETED
