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
from app.presentation.cli.report import main, render

DAY = date(2026, 11, 4)
AT = datetime(2026, 11, 4, 3, 0, tzinfo=UTC)
OUT_OF_CREDIT = FailureCause(("CourseSelectionError", "RateLimitError"), "insufficient_quota")
NANO_MILLION = {"gpt-5.4-nano": TokenUsage(1_000_000, 0, 0)}


def report_of(*builds: PlanBuild) -> BuildReport:
    counted = tally([RecordedBuild(AT, 2.0, build) for build in builds])
    return BuildReport(DAY, DAY, [(DAY, counted)], counted)


def test_each_day_shows_its_counts_cost_per_build_times_and_failures() -> None:
    succeeded = PlanBuild(
        BuildOutcome.SUCCEEDED,
        None,
        {PlanStage.ANALYZING: 10.0, PlanStage.SELECTING: 30.0},
        NANO_MILLION,
    )
    failed = PlanBuild(BuildOutcome.FAILED, OUT_OF_CREDIT, {PlanStage.ANALYZING: 4.0})

    lines = render(report_of(succeeded, failed)).splitlines()

    assert lines[0] == "2026-11-04 〜 2026-11-04(日本時間)に作り終えた道標"
    assert lines[1] == "11-04  2 件(成功 1、失敗 1)、費用 30.00 円(1 件 15.00 円)"
    assert lines[2] == "       待ち 中央 2.0 秒、最大 2.0 秒 / 作る 中央 22.0 秒、最大 40.0 秒"
    assert lines[3] == (
        "       失敗 1 件: CourseSelectionError ← RateLimitError(insufficient_quota: 残高切れ)"
    )
    assert "残高切れで失敗した道標が 1 件あります。OpenAI の残高を確かめてください" in lines


def test_stalled_builds_are_not_counted_in_the_cost_per_build() -> None:
    lines = render(
        report_of(
            PlanBuild(BuildOutcome.SUCCEEDED, None, {}, NANO_MILLION),
            PlanBuild(BuildOutcome.STALLED),
        )
    ).splitlines()

    assert lines[1] == "11-04  2 件(成功 1、止まった 1)、費用 30.00 円(1 件 30.00 円)"
    assert lines[2] == "       待ち 中央 2.0 秒、最大 2.0 秒 / 作る -"


def test_the_total_lists_tokens_and_cost_by_model_and_names_models_without_a_price() -> None:
    usage = NANO_MILLION | {"other-model": TokenUsage(5, 0, 5)}

    lines = render(report_of(PlanBuild(BuildOutcome.SUCCEEDED, None, {}, usage))).splitlines()

    assert "       gpt-5.4-nano: 入力 1,000,000(うちキャッシュ 0)、出力 0、30.00 円" in lines
    assert lines[-1] == "料金表に無いモデルは費用に入れていません: other-model"


def test_a_period_without_builds_says_so() -> None:
    report = BuildReport(DAY, DAY, [], tally([]))

    assert render(report).splitlines()[1] == "記録はありません"


def test_a_report_of_no_days_is_refused_before_touching_the_database(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        main(["--days", "0"])

    assert "1 以上にしてください" in capsys.readouterr().err
