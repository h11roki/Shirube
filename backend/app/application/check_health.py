from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.ports import (
    OUT_OF_CREDIT,
    BuildOutcome,
    PlanBuildLog,
    PlanRepository,
    RecordedBuild,
)


@dataclass(frozen=True)
class Health:
    queue_stalled: bool
    out_of_credit: bool


def _reached_openai(recorded: RecordedBuild) -> bool:
    build = recorded.build
    return build.outcome is BuildOutcome.FAILED or (
        build.outcome is BuildOutcome.SUCCEEDED and bool(build.usage)
    )


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
        reached = [
            recorded
            for recorded in self._builds.since(moment - self._credit_window)
            if _reached_openai(recorded)
        ]
        last = max(reached, key=lambda recorded: recorded.finished_at, default=None)
        return Health(
            queue_stalled=waiting_since is not None and moment - waiting_since > self._stall_after,
            out_of_credit=last is not None
            and last.build.cause is not None
            and last.build.cause.code == OUT_OF_CREDIT,
        )
