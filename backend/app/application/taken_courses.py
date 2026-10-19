from uuid import UUID

from app.application.ports import UserRepository


class TakenCourses:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def names(self, owner_id: UUID) -> list[str]:
        return sorted(self._users.taken(owner_id))

    def forget(self, owner_id: UUID, name: str) -> list[str]:
        self._users.remove_taken(owner_id, name)
        return self.names(owner_id)
