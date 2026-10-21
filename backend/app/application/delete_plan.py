from uuid import UUID

from app.application.ports import PlanRepository


class DeletePlan:
    def __init__(self, plans: PlanRepository) -> None:
        self._plans = plans

    def run(self, *, owner_id: UUID, plan_id: UUID) -> bool:
        return self._plans.delete_owned_by(plan_id, owner_id)
