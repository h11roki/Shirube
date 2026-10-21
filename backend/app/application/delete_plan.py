from uuid import UUID

from app.application.ports import PlanRepository
from app.domain.plan import PlanStatus


class PlanRunningError(ValueError):
    pass


class DeletePlan:
    def __init__(self, plans: PlanRepository) -> None:
        self._plans = plans

    def run(self, *, owner_id: UUID, plan_id: UUID) -> bool:
        if self._plans.delete_owned_by(plan_id, owner_id):
            return True
        plan = self._plans.get_owned_by(plan_id, owner_id)
        if plan is not None and plan.status is PlanStatus.RUNNING:
            raise PlanRunningError("作っている途中の道標は、できてから消せます")
        return False
