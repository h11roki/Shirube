from dataclasses import dataclass
from uuid import UUID

from app.application.ports import PlanRepository
from app.domain.plan import PlanSummary

PLAN_LIST_LIMIT = 50


@dataclass(frozen=True)
class PlanListing:
    summaries: list[PlanSummary]
    total: int


class ListPlans:
    def __init__(self, plans: PlanRepository) -> None:
        self._plans = plans

    def run(self, owner_id: UUID) -> PlanListing:
        return PlanListing(
            self._plans.list_owned_by(owner_id, PLAN_LIST_LIMIT),
            self._plans.count_owned_by(owner_id),
        )
