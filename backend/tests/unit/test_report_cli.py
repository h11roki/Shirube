from datetime import UTC, date, datetime

import pytest

from app.application.ports import (
    BuildOutcome,
    FailureCause,
    PlanBuild,
    RecordedBuild,
    TokenUsage,
)
from app.application.report_plan_builds import BuildReport, tally
from app.domain.plan import PlanStage
from app.presentation.cli.report import INDENT, MAX_DAYS, main, render

DAY = date(2026, 11, 4)
AT = datetime(2026, 11, 4, 3, 0, tzinfo=UTC)
OUT_OF_CREDIT = FailureCause(("CourseSelectionError", "RateLimitError"), "insufficient_quota")
NANO_MILLION = {"gpt-5.4-nano": TokenUsage(1_000_000, 0, 0)}
OUT_OF_CREDIT_LINE = (
    f"{INDENT}失敗の原因 1 回: CourseSelectionError ← RateLimitError(insufficient_quota: 残高切れ)"
)
OUT_OF_CREDIT_WARNING = "残高切れで失敗した回が 1 回あります。OpenAI の残高を確かめてください"


def report_of(*builds: PlanBuild) -> BuildReport:
    counted = tally([RecordedBuild(AT, 2.0, build) for build in builds])
    return BuildReport(DAY, DAY, [(DAY, counted)], counted)


def test_each_day_shows_its_counts_cost_per_run_times_and_failures() -> None:
    succeeded = PlanBuild(
        BuildOutcome.SUCCEEDED,
        None,
        {PlanStage.ANALYZING: 10.0, PlanStage.SELECTING: 30.0},
        NANO_MILLION,
    )
    failed = PlanBuild(BuildOutcome.FAILED, OUT_OF_CREDIT, {PlanStage.ANALYZING: 4.0})

    lines = render(report_of(succeeded, failed)).splitlines()

    assert lines[0] == "2026-11-04 〜 2026-11-04(日本時間)に作り終えた道標"
    assert lines[1] == "2026-11-04  2 件(成功 1、失敗 1)、費用 30.00 円(1 回 15.00 円)"
    assert lines[2] == f"{INDENT}待ち 中央 2.0 秒、最大 2.0 秒 / 作る 中央 22.0 秒、最大 40.0 秒"
    assert lines[3] == OUT_OF_CREDIT_LINE
    assert lines[-1] == OUT_OF_CREDIT_WARNING


def test_stalled_builds_are_not_counted_in_the_cost_per_run() -> None:
    lines = render(
        report_of(
            PlanBuild(BuildOutcome.SUCCEEDED, None, {}, NANO_MILLION),
            PlanBuild(BuildOutcome.STALLED),
        )
    ).splitlines()

    assert lines[1] == "2026-11-04  2 件(成功 1、止まった 1)、費用 30.00 円(1 回 30.00 円)"
    assert lines[2] == f"{INDENT}待ち 中央 2.0 秒、最大 2.0 秒 / 作る -"


def test_work_thrown_away_after_a_stall_is_not_a_plan_but_its_failure_is_shown() -> None:
    lines = render(
        report_of(
            PlanBuild(BuildOutcome.STALLED),
            PlanBuild(BuildOutcome.DISCARDED, OUT_OF_CREDIT, {PlanStage.ANALYZING: 1300.0}),
        )
    ).splitlines()

    assert lines[1] == "2026-11-04  1 件(止まった 1)、費用 0.00 円(1 回 0.00 円)"
    assert lines[3] == f"{INDENT}止まったあとに作り終えて捨てた 1 回(費用と作る時間に入れた)"
    assert lines[4] == OUT_OF_CREDIT_LINE
    assert lines[-1] == OUT_OF_CREDIT_WARNING


def test_the_total_lists_cost_by_model_and_names_models_without_a_price() -> None:
    usage = NANO_MILLION | {"other-model": TokenUsage(5, 0, 5)}

    lines = render(report_of(PlanBuild(BuildOutcome.SUCCEEDED, None, {}, usage))).splitlines()

    assert lines[1] == "2026-11-04  1 件(成功 1)、費用 30.00 円"
    assert f"{INDENT}gpt-5.4-nano: 入力 1,000,000(うちキャッシュ 0)、出力 0、30.00 円" in lines
    assert f"{INDENT}other-model: 入力 5(うちキャッシュ 0)、出力 5、料金表に無い" in lines
    assert lines[-1] == "料金表に無いモデルは費用に入れていません: other-model"


def test_a_period_without_tokens_has_no_section_by_model() -> None:
    lines = render(report_of(PlanBuild(BuildOutcome.STALLED))).splitlines()

    assert "モデルごと" not in lines


def test_a_period_without_builds_says_so() -> None:
    report = BuildReport(DAY, DAY, [], tally([]))

    assert render(report).splitlines()[1] == "記録はありません"


@pytest.mark.parametrize("days", ["0", str(MAX_DAYS + 1)])
def test_a_number_of_days_out_of_range_is_refused_before_touching_the_database(
    days: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        main(["--days", days])

    assert f"1〜{MAX_DAYS} にしてください" in capsys.readouterr().err
