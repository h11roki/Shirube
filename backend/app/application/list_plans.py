from uuid import UUID

from app.application.ports import PlanRepository
from app.domain.plan import PlanSummary

PLAN_LIST_LIMIT = 50


class ListPlans:
    def __init__(self, plans: PlanRepository) -> None:
        self._plans = plans

    def run(self, owner_id: UUID) -> list[PlanSummary]:
        return self._plans.list_owned_by(owner_id, PLAN_LIST_LIMIT)
