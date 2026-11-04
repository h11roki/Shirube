import argparse
import sys
from collections.abc import Sequence
from statistics import median

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.ports import BuildOutcome
from app.application.report_plan_builds import BuildReport, BuildTally
from app.presentation.cli.prices import price_of, unpriced, yen
from app.presentation.composition import database_engine, load_settings, report_plan_builds

DEFAULT_DAYS = 14
MAX_DAYS = 3650
OUT_OF_CREDIT = "insufficient_quota"
OUTCOME_LABELS = {
    BuildOutcome.SUCCEEDED: "成功",
    BuildOutcome.FAILED: "失敗",
    BuildOutcome.STALLED: "止まった",
}
CODE_NOTES = {OUT_OF_CREDIT: ": 残高切れ"}
TOTAL_HEADING = "合計      "
INDENT = " " * 12


def render(report: BuildReport) -> str:
    lines = [f"{report.first_day} 〜 {report.last_day}(日本時間)に作り終えた道標"]
    if not report.days:
        return "\n".join([*lines, "記録はありません"])
    for day, tally in report.days:
        lines.extend(_tally_lines(str(day), tally))
    lines.extend(_tally_lines(TOTAL_HEADING, report.total))
    if report.total.usage:
        lines.append("モデルごと")
        lines.extend(
            f"{INDENT}{model}: 入力 {tokens.input:,}(うちキャッシュ {tokens.cached:,})、"
            f"出力 {tokens.output:,}、"
            + (f"{yen({model: tokens}):.2f} 円" if price_of(model) else "料金表に無い")
            for model, tokens in report.total.usage.items()
        )
    if missing := unpriced(list(report.total.usage)):
        lines.append(f"料金表に無いモデルは費用に入れていません: {'、'.join(missing)}")
    out_of_credit = sum(
        count for cause, count in report.total.causes.items() if cause.code == OUT_OF_CREDIT
    )
    if out_of_credit:
        lines.append(
            f"残高切れで失敗した回が {out_of_credit} 回あります。OpenAI の残高を確かめてください"
        )
    return "\n".join(lines)


def _tally_lines(heading: str, tally: BuildTally) -> list[str]:
    outcomes = "、".join(
        f"{label} {tally.outcomes[outcome]}"
        for outcome, label in OUTCOME_LABELS.items()
        if tally.outcomes[outcome]
    )
    cost = yen(tally.usage)
    priced = tally.metered and not unpriced(list(tally.usage))
    per_run = f"(1 回 {cost / tally.metered:.2f} 円)" if priced else ""
    lines = [
        f"{heading}  {tally.builds} 件{f'({outcomes})' if outcomes else ''}、"
        f"費用 {cost:.2f} 円{per_run}",
        f"{INDENT}待ち {_spread(tally.queued_seconds)} / 作る {_spread(tally.build_seconds)}",
    ]
    if discarded := tally.outcomes[BuildOutcome.DISCARDED]:
        lines.append(
            f"{INDENT}止まったあとに作り終えて捨てた {discarded} 回(費用と作る時間に入れた)"
        )
    lines.extend(
        f"{INDENT}失敗の原因 {count} 回: {' ← '.join(cause.types)}"
        + ("" if cause.code is None else f"({cause.code}{CODE_NOTES.get(cause.code, '')})")
        for cause, count in tally.causes.most_common()
    )
    return lines


def _spread(seconds: Sequence[float]) -> str:
    if not seconds:
        return "-"
    return f"中央 {median(seconds):.1f} 秒、最大 {max(seconds):.1f} 秒"


def _days(text: str) -> int:
    days = int(text)
    if not 1 <= days <= MAX_DAYS:
        raise argparse.ArgumentTypeError(f"1〜{MAX_DAYS} にしてください: {text}")
    return days


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="道標を作った記録(ADR 0087)を、日本時間の日ごとに件数、時間、費用で出す"
    )
    parser.add_argument(
        "--days", type=_days, default=DEFAULT_DAYS, help=f"今日を含む日数。既定は {DEFAULT_DAYS}"
    )
    args = parser.parse_args(argv)
    engine = database_engine(load_settings())
    try:
        print(render(report_plan_builds(engine).run(args.days)))
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
