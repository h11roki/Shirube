from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.application.ports import Deletion, PlanRunningError, UserRepository
from app.domain.quota import day_start


class DeleteAccount:
    def __init__(self, users: UserRepository, now: Callable[[], datetime]) -> None:
        self._users = users
        self._now = now

    def run(self, user_id: UUID) -> None:
        if self._users.delete(user_id, day_start(self._now())) is Deletion.RUNNING:
            raise PlanRunningError("作っている途中の道標ができてから退会できます")
