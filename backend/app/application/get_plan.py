from uuid import UUID

from app.application.ports import PlanRepository
from app.domain.plan import Plan


class GetPlan:
    def __init__(self, plans: PlanRepository) -> None:
        self._plans = plans

    def run(self, plan_id: UUID, owner_id: UUID) -> Plan | None:
        return self._plans.get_owned_by(plan_id, owner_id)
