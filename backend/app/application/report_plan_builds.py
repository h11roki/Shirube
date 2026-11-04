from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.application.ports import (
    BuildOutcome,
    FailureCause,
    PlanBuildLog,
    RecordedBuild,
    TokenUsage,
    total_usage,
)
from app.domain.course import UNIVERSITY_TIME


@dataclass(frozen=True)
class BuildTally:
    outcomes: Counter[BuildOutcome]
    causes: Counter[FailureCause]
    queued_seconds: tuple[float, ...]
    build_seconds: tuple[float, ...]
    usage: dict[str, TokenUsage]

    @property
    def builds(self) -> int:
        return self.outcomes.total()

    @property
    def metered(self) -> int:
        return self.builds - self.outcomes[BuildOutcome.STALLED]


@dataclass(frozen=True)
class BuildReport:
    first_day: date
    last_day: date
    days: list[tuple[date, BuildTally]]
    total: BuildTally


class ReportPlanBuilds:
    def __init__(self, builds: PlanBuildLog, now: Callable[[], datetime]) -> None:
        self._builds = builds
        self._now = now

    def run(self, days: int) -> BuildReport:
        if days < 1:
            raise ValueError(f"日数は 1 以上にしてください: {days}")
        last_day = self._now().astimezone(UNIVERSITY_TIME).date()
        first_day = last_day - timedelta(days=days - 1)
        records = self._builds.since(datetime.combine(first_day, time(), UNIVERSITY_TIME))
        by_day: defaultdict[date, list[RecordedBuild]] = defaultdict(list)
        for recorded in records:
            by_day[recorded.finished_at.astimezone(UNIVERSITY_TIME).date()].append(recorded)
        return BuildReport(
            first_day,
            last_day,
            [(day, tally(by_day[day])) for day in sorted(by_day)],
            tally(records),
        )


def tally(records: Sequence[RecordedBuild]) -> BuildTally:
    builds = [recorded.build for recorded in records]
    return BuildTally(
        Counter(build.outcome for build in builds),
        Counter(build.cause for build in builds if build.cause is not None),
        tuple(
            recorded.queued_seconds for recorded in records if recorded.queued_seconds is not None
        ),
        tuple(sum(build.seconds.values()) for build in builds if build.seconds),
        total_usage(build.usage for build in builds),
    )
