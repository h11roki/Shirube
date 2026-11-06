from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.ports import (
    OUT_OF_CREDIT,
    BuildOutcome,
    PlanBuildLog,
    PlanRepository,
)


@dataclass(frozen=True)
class Health:
    queue_stalled: bool
    out_of_credit: bool


class CheckHealth:
    def __init__(
        self,
        plans: PlanRepository,
        builds: PlanBuildLog,
        now: Callable[[], datetime],
        stall_after: timedelta,
        credit_window: timedelta,
    ) -> None:
        self._plans = plans
        self._builds = builds
        self._now = now
        self._stall_after = stall_after
        self._credit_window = credit_window

    def run(self) -> Health:
        moment = self._now()
        waiting_since = self._plans.oldest_waiting()
        recent = self._builds.since(moment - self._credit_window)
        ran_out = [
            recorded.finished_at
            for recorded in recent
            if recorded.build.cause is not None and recorded.build.cause.code == OUT_OF_CREDIT
        ]
        paid = [
            recorded.finished_at
            for recorded in recent
            if recorded.build.outcome is BuildOutcome.SUCCEEDED and recorded.build.usage
        ]
        return Health(
            queue_stalled=waiting_since is not None and moment - waiting_since > self._stall_after,
            out_of_credit=bool(ran_out) and (not paid or max(ran_out) > max(paid)),
        )
