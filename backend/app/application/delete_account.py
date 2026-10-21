from uuid import UUID

from app.application.ports import UserRepository


class DeleteAccount:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def run(self, user_id: UUID) -> None:
        self._users.delete(user_id)
