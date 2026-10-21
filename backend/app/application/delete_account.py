from uuid import UUID

from app.application.ports import PlanRepository, UserRepository


class DeleteAccount:
    def __init__(self, plans: PlanRepository, users: UserRepository) -> None:
        self._plans = plans
        self._users = users

    def run(self, user_id: UUID) -> None:
        self._plans.delete_all_owned_by(user_id)
        self._users.delete(user_id)
