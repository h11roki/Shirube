from collections import Counter
from datetime import UTC, date, datetime, timedelta

from app.application.ports import (
    BuildOutcome,
    FailureCause,
    PlanBuild,
    RecordedBuild,
    TokenUsage,
)
from app.application.report_plan_builds import ReportPlanBuilds, tally
from app.domain.course import UNIVERSITY_TIME
from app.domain.plan import PlanStage
from tests.fakes import FakePlanBuildLog

NOW = datetime(2026, 11, 4, 3, 0, tzinfo=UTC)
TIMEOUT = FailureCause(("CourseSelectionError", "APITimeoutError"))
NANO = "gpt-5.4-nano"


def built(at: datetime, build: PlanBuild, queued: float | None = 1.0) -> RecordedBuild:
    return RecordedBuild(at, queued, build)


def test_builds_are_counted_by_the_japanese_day_they_finished_on() -> None:
    late_on_the_3rd = datetime(2026, 11, 3, 14, 59, tzinfo=UTC)
    early_on_the_4th = datetime(2026, 11, 3, 15, 0, tzinfo=UTC)
    log = FakePlanBuildLog(
        [
            built(late_on_the_3rd, PlanBuild(BuildOutcome.SUCCEEDED)),
            built(early_on_the_4th, PlanBuild(BuildOutcome.FAILED, TIMEOUT)),
            built(NOW, PlanBuild(BuildOutcome.SUCCEEDED)),
        ]
    )

    report = ReportPlanBuilds(log, lambda: NOW).run(days=2)

    assert (report.first_day, report.last_day) == (date(2026, 11, 3), date(2026, 11, 4))
    assert log.starts == [datetime(2026, 11, 3, tzinfo=UNIVERSITY_TIME)]
    assert [(day, tally.outcomes) for day, tally in report.days] == [
        (date(2026, 11, 3), Counter({BuildOutcome.SUCCEEDED: 1})),
        (date(2026, 11, 4), Counter({BuildOutcome.SUCCEEDED: 1, BuildOutcome.FAILED: 1})),
    ]
    assert report.total.builds == 3


def test_a_tally_adds_up_tokens_seconds_and_causes_and_leaves_out_what_was_not_measured() -> None:
    stages = {PlanStage.ANALYZING: 2.0, PlanStage.SEARCHING: 1.0, PlanStage.SELECTING: 30.0}
    records = [
        built(
            NOW,
            PlanBuild(
                BuildOutcome.SUCCEEDED,
                None,
                stages | {PlanStage.PLACING: 0.5},
                {NANO: TokenUsage(100, 10, 5)},
            ),
            queued=4.0,
        ),
        built(
            NOW,
            PlanBuild(
                BuildOutcome.FAILED,
                TIMEOUT,
                stages,
                {NANO: TokenUsage(50, 0, 1), "gpt-5.4-mini": TokenUsage(7, 0, 3)},
            ),
            queued=None,
        ),
        built(NOW, PlanBuild(BuildOutcome.FAILED, TIMEOUT), queued=2.0),
        built(NOW, PlanBuild(BuildOutcome.STALLED), queued=60.0),
    ]

    counted = tally(records)

    assert counted.builds == 4
    assert counted.metered == 3
    assert counted.causes == Counter({TIMEOUT: 2})
    assert counted.queued_seconds == (4.0, 2.0, 60.0)
    assert counted.build_seconds == (33.5, 33.0)
    assert counted.usage == {
        "gpt-5.4-mini": TokenUsage(7, 0, 3),
        NANO: TokenUsage(150, 10, 6),
    }


def test_a_day_without_builds_is_left_out() -> None:
    log = FakePlanBuildLog([built(NOW - timedelta(days=2), PlanBuild(BuildOutcome.SUCCEEDED))])

    report = ReportPlanBuilds(log, lambda: NOW).run(days=3)

    assert [day for day, _ in report.days] == [date(2026, 11, 2)]


def test_work_thrown_away_after_its_plan_stalled_adds_cost_and_time_but_not_a_plan() -> None:
    thrown_away = PlanBuild(
        BuildOutcome.DISCARDED,
        TIMEOUT,
        {PlanStage.ANALYZING: 1300.0},
        {NANO: TokenUsage(100, 0, 10)},
    )

    counted = tally(
        [
            built(NOW, PlanBuild(BuildOutcome.STALLED), queued=3.0),
            built(NOW, thrown_away, queued=3.0),
        ]
    )

    assert (counted.builds, counted.metered) == (1, 1)
    assert counted.causes == Counter()
    assert counted.queued_seconds == (3.0,)
    assert counted.build_seconds == (1300.0,)
    assert counted.usage == {NANO: TokenUsage(100, 0, 10)}
