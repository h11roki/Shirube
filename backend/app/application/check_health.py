import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.ports import OUT_OF_CREDIT, PlanBuildLog, PlanRepository, RecordedBuild

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Health:
    database_reachable: bool
    queue_stalled: bool | None = None
    out_of_credit: bool | None = None


def _ran_out_of_credit(recorded: RecordedBuild) -> bool:
    cause = recorded.build.cause
    return cause is not None and cause.code == OUT_OF_CREDIT


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
        try:
            waiting_since = self._plans.oldest_waiting()
            recent = self._builds.since(moment - self._credit_window)
        except Exception:
            logger.exception("health: DB を読めませんでした")
            return Health(database_reachable=False)
        called_openai = [
            recorded for recorded in recent if recorded.build.usage or _ran_out_of_credit(recorded)
        ]
        last = max(called_openai, key=lambda recorded: recorded.finished_at, default=None)
        return Health(
            database_reachable=True,
            queue_stalled=waiting_since is not None and moment - waiting_since > self._stall_after,
            out_of_credit=last is not None and _ran_out_of_credit(last),
        )
