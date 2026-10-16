from uuid import UUID

from app.application.ports import PlanRepository
from app.domain.plan import Plan


class GetPlan:
    def __init__(self, plans: PlanRepository) -> None:
        self._plans = plans

    def run(self, plan_id: UUID, owner_id: UUID) -> Plan | None:
        plan = self._plans.get(plan_id)
        if plan is None or plan.owner_id != owner_id:
            return None
        return plan
