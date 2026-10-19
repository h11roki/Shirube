from uuid import UUID

from app.application.ports import UserRepository


class ForgetTakenCourse:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def run(self, owner_id: UUID, name: str) -> None:
        self._users.remove_taken(owner_id, name)
