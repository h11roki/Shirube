from uuid import UUID

from app.application.ports import PlanRepository
from app.domain.plan import Plan


class GetPlan:
    def __init__(self, plans: PlanRepository) -> None:
        self._plans = plans

    def run(self, *, owner_id: UUID, plan_id: UUID) -> Plan | None:
        return self._plans.get_owned_by(plan_id, owner_id)
