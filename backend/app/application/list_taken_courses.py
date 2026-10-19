from uuid import UUID

from app.application.ports import UserRepository


class ListTakenCourses:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def run(self, owner_id: UUID) -> list[str]:
        return sorted(self._users.taken(owner_id))
