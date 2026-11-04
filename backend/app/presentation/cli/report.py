import argparse
import sys
from collections.abc import Sequence
from statistics import median

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.ports import BuildOutcome, FailureCause
from app.application.report_plan_builds import BuildReport, BuildTally
from app.presentation.cli.prices import unpriced, yen
from app.presentation.composition import database_engine, load_settings, report_plan_builds

DEFAULT_DAYS = 14
OUT_OF_CREDIT = "insufficient_quota"
OUTCOME_LABELS = {
    BuildOutcome.SUCCEEDED: "成功",
    BuildOutcome.FAILED: "失敗",
    BuildOutcome.DISCARDED: "捨てた",
    BuildOutcome.STALLED: "止まった",
}
CODE_LABELS = {OUT_OF_CREDIT: "残高切れ"}
INDENT = " " * 7


def render(report: BuildReport) -> str:
    lines = [f"{report.first_day} 〜 {report.last_day}(日本時間)に作り終えた道標"]
    if not report.days:
        return "\n".join([*lines, "記録はありません"])
    for day, tally in report.days:
        lines.extend(_tally_lines(f"{day:%m-%d}", tally))
    lines.extend(_tally_lines("合計 ", report.total))
    lines.append("モデルごと")
    lines.extend(
        f"{INDENT}{model}: 入力 {tokens.input:,}(うちキャッシュ {tokens.cached:,})、"
        f"出力 {tokens.output:,}、{yen({model: tokens}):.2f} 円"
        for model, tokens in report.total.usage.items()
    )
    if missing := unpriced(list(report.total.usage)):
        lines.append(f"料金表に無いモデルは費用に入れていません: {'、'.join(missing)}")
    out_of_credit = sum(
        count for cause, count in report.total.causes.items() if cause.code == OUT_OF_CREDIT
    )
    if out_of_credit:
        lines.append(
            f"残高切れで失敗した道標が {out_of_credit} 件あります。OpenAI の残高を確かめてください"
        )
    return "\n".join(lines)


def _tally_lines(heading: str, tally: BuildTally) -> list[str]:
    outcomes = "、".join(
        f"{OUTCOME_LABELS[outcome]} {tally.outcomes[outcome]}"
        for outcome in BuildOutcome
        if tally.outcomes[outcome]
    )
    cost = yen(tally.usage)
    per_build = f"(1 件 {cost / tally.metered:.2f} 円)" if tally.metered else ""
    return [
        f"{heading}  {tally.builds} 件({outcomes})、費用 {cost:.2f} 円{per_build}",
        f"{INDENT}待ち {_spread(tally.queued_seconds)} / 作る {_spread(tally.build_seconds)}",
        *(
            f"{INDENT}失敗 {count} 件: {_cause(cause)}"
            for cause, count in tally.causes.most_common()
        ),
    ]


def _spread(seconds: Sequence[float]) -> str:
    if not seconds:
        return "-"
    return f"中央 {median(seconds):.1f} 秒、最大 {max(seconds):.1f} 秒"


def _cause(cause: FailureCause) -> str:
    chain = " ← ".join(cause.types)
    if cause.code is None:
        return chain
    label = CODE_LABELS.get(cause.code)
    return f"{chain}({cause.code}{'' if label is None else f': {label}'})"


def _days(text: str) -> int:
    days = int(text)
    if days < 1:
        raise argparse.ArgumentTypeError(f"1 以上にしてください: {text}")
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
