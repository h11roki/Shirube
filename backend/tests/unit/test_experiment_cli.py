import argparse
from collections.abc import Iterator, Sequence
from typing import Any

import pytest
from langchain_core.messages import HumanMessage

from app.application.evaluate_selection import Judgment, Pick, SelectionResult, UnlinkedPick
from app.application.ports import TokenUsage
from app.application.run_experiment import (
    ExperimentSummary,
    FailedTrial,
    Spread,
    StageSeconds,
    Trial,
)
from app.application.search_courses import SearchError
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import (
    CourseChoice,
    Recommendation,
    RecommendedCourse,
    Relevance,
)
from app.infrastructure.llm.usage_meter import LangChainUsageMeter
from app.presentation.cli.experiment import (
    METRICS,
    collect,
    compare,
    label,
    main,
    render,
    summary_document,
    trial_document,
    unpriced,
    yen,
)
from tests.fakes import chat_answering

PROFILE = OccupationProfile("職業", "職業", None, ("甲", "乙", "丙"))
THIRTY_YEN = {"gpt-5.4-nano": TokenUsage(1_000_000, 0, 0)}


def test_cost_counts_cached_input_at_its_own_price_and_matches_dated_model_names() -> None:
    usage = {"gpt-5.4-nano-2026-03-17": TokenUsage(1_000_000, 200_000, 100_000)}

    assert yen(usage) == pytest.approx((0.8 * 0.20 + 0.2 * 0.02 + 0.1 * 1.25) * 150)


def test_models_without_a_price_cost_nothing_and_are_listed() -> None:
    usage = {"gpt-5.4-mini": TokenUsage(1_000_000, 0, 0), "other-model": TokenUsage(5, 0, 5)}

    assert yen(usage) == pytest.approx(0.75 * 150)
    assert unpriced(list(usage)) == ["other-model"]


def test_the_meter_reads_token_usage_from_langchain_by_model() -> None:
    chat = chat_answering({"content": "はい"})

    with LangChainUsageMeter().meter() as usage:
        answer = chat.invoke([HumanMessage("質問")])

    assert answer.content == "はい"
    assert usage() == {"test-model": TokenUsage(input=1, cached=0, output=1)}


def test_the_meter_keeps_the_usage_of_a_call_that_failed_afterwards() -> None:
    chat = chat_answering({"content": "はい"})

    with pytest.raises(RuntimeError), LangChainUsageMeter().meter() as usage:
        chat.invoke([HumanMessage("質問")])
        raise RuntimeError("答えを使えない")

    assert usage() == {"test-model": TokenUsage(input=1, cached=0, output=1)}


def test_an_outer_meter_also_counts_the_calls_of_an_inner_one_that_was_interrupted() -> None:
    chat = chat_answering({"content": "はい"})
    meter = LangChainUsageMeter()

    with meter.meter() as outer:
        with pytest.raises(KeyboardInterrupt), meter.meter() as inner:
            chat.invoke([HumanMessage("質問")])
            raise KeyboardInterrupt
        chat.invoke([HumanMessage("質問")])

    assert inner() == {"test-model": TokenUsage(input=1, cached=0, output=1)}
    assert outer() == {"test-model": TokenUsage(input=2, cached=0, output=2)}


@pytest.mark.parametrize("text", ["baseline", "vote-3", "nano_0.2"])
def test_a_label_of_letters_digits_dots_and_dashes_is_accepted(text: str) -> None:
    assert label(text) == text


@pytest.mark.parametrize("text", ["mini/nano", "", "-start", "日本語"])
def test_a_label_that_cannot_be_a_file_name_part_is_refused(text: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        label(text)


@pytest.mark.parametrize("budget", ["0", "-1", "nan", "inf"])
def test_a_budget_that_cannot_stop_the_run_is_refused(budget: str) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["run", "--label", "x", "--budget", budget])

    assert stopped.value.code == 2


def succeeded(repeat: int) -> Trial:
    return Trial(
        "職業",
        repeat,
        Recommendation(PROFILE, (), ()),
        SelectionResult("職業", (), (), ()),
        THIRTY_YEN,
        StageSeconds(1.0, 1.0, 1.0),
    )


def test_the_raw_output_keeps_the_reading_and_the_reason_of_a_dropped_foundation() -> None:
    reading = OccupationProfile("職業", "読んだ職業", "前提", ("甲", "乙", "丙"))
    recommendation = Recommendation(
        reading,
        (RecommendedCourse("科目A", "10000", Relevance.CORE, "理由A"),),
        ("科目A", "科目B", "科目C"),
        (CourseChoice("科目B", Relevance.FOUNDATION, "理由B", "科目C"),),
    )
    outcome = Trial(
        "職業",
        1,
        recommendation,
        SelectionResult(
            "職業",
            (Pick("科目A", Relevance.CORE, Judgment.EXPECTED),),
            (),
            (UnlinkedPick("科目B", "科目C", Judgment.FOUNDATION),),
        ),
        THIRTY_YEN,
        StageSeconds(1.0, 1.0, 1.0),
    )

    written = trial_document(outcome)

    assert (written["interpretation"], written["assumption"]) == ("読んだ職業", "前提")
    assert written["unlinked"] == [
        {
            "name": "科目B",
            "judgment": "foundation",
            "reason": "理由B",
            "prerequisite_for": "科目C",
        }
    ]


def failed(repeat: int) -> FailedTrial:
    return FailedTrial("職業", repeat, "失敗", THIRTY_YEN)


class Paid:
    def __init__(self, outcomes: Sequence[Trial | FailedTrial | BaseException]) -> None:
        self._outcomes = outcomes
        self._usage: dict[str, TokenUsage] = {}

    def __iter__(self) -> Iterator[Trial | FailedTrial]:
        for outcome in self._outcomes:
            if isinstance(outcome, BaseException):
                raise outcome
            for model, tokens in outcome.usage.items():
                self._usage[model] = self._usage[model] + tokens if model in self._usage else tokens
            yield outcome

    def spent(self) -> dict[str, TokenUsage]:
        return dict(self._usage)


def test_collect_stops_before_the_next_recommendation_once_the_budget_is_spent() -> None:
    paid = Paid([succeeded(1), succeeded(2), succeeded(3)])

    collection = collect(iter(paid), 3, 50, paid.spent)

    assert len(collection.outcomes) == 2
    assert (collection.stopped, collection.over_budget) == ("費用の上限 50 円に達した", True)


def test_collect_finishes_when_the_last_recommendation_crosses_the_budget() -> None:
    paid = Paid([succeeded(1), succeeded(2)])

    collection = collect(iter(paid), 2, 50, paid.spent)

    assert len(collection.outcomes) == 2
    assert (collection.stopped, collection.over_budget) == (None, False)


def test_collect_stops_after_three_failures_in_a_row() -> None:
    paid = Paid([failed(1), succeeded(2), failed(3), failed(4), failed(5), succeeded(6)])

    collection = collect(iter(paid), 6, 1000, paid.spent)

    assert len(collection.outcomes) == 5
    assert (collection.stopped, collection.over_budget) == ("推薦が 3 回続けて失敗した", False)


def test_collect_stops_when_a_model_without_a_price_answered() -> None:
    paid = Paid([FailedTrial("職業", 1, "失敗", {"other-model": TokenUsage(1, 0, 1)})])

    collection = collect(iter(paid), 2, 1000, paid.spent)

    assert collection.stopped == "料金表に無いモデルが答えた: other-model"


@pytest.mark.parametrize(
    ("error", "stopped"),
    [
        (SearchError("シラバスが DB にありません: 10000"), "シラバスが DB にありません: 10000"),
        (OSError("応答が無い"), "入出力に失敗しました: 応答が無い"),
        (KeyboardInterrupt(), "中断した"),
        (RuntimeError("壊れた"), "思わぬ失敗で止まった: RuntimeError('壊れた')"),
    ],
    ids=["search", "input-output", "interrupted", "unexpected"],
)
def test_collect_keeps_what_ran_before_the_run_was_stopped(
    error: BaseException, stopped: str
) -> None:
    paid = Paid([succeeded(1), error, succeeded(2)])

    collection = collect(iter(paid), 2, 1000, paid.spent)

    assert collection.outcomes == [succeeded(1)]
    assert (collection.stopped, collection.over_budget) == (stopped, False)


def spread(value: float, std: float) -> dict[str, float]:
    return {"mean": value, "std": std, "low": value - std, "high": value + std}


def document(summary: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "label": "baseline",
        "created": "2026-10-23T04:00:00+09:00",
        "commit": "abc1234",
        "stopped": None,
        "spent_yen": 24.0,
        "config": {
            "occupations": 10,
            "repeats": 3,
            "profiles": "analyzed",
            "chat_model": "gpt-5.4-mini",
            "selection_model": "gpt-5.4-nano",
            "candidate_limit": 30,
        },
        "summary": summary,
    }


def test_the_summary_document_names_every_metric_it_shows() -> None:
    value = Spread(0.5, 0.1, 0.4, 0.6)
    summary = ExperimentSummary(
        trials=2,
        failures=0,
        complete_repeats=2,
        scored_repeats=2,
        recall=(value, value),
        candidate_recall=value,
        core_precision=None,
        expected_as_core=value,
        unrelated=value,
        cores=value,
        foundations=value,
        overlap=None,
        core_overlap=None,
        usage=THIRTY_YEN,
        seconds=StageSeconds(1.0, 2.0, 3.0),
    )

    written = summary_document(summary)

    assert {key for key, _, _ in METRICS} <= written.keys()
    assert written["core_precision"] is None
    assert written["yen_per_plan"] == pytest.approx(15.0)
    assert "  中心の適合率 -" in render(document(written)).splitlines()


def test_a_run_whose_recommendations_all_failed_is_shown_without_scores() -> None:
    lines = render(document(None)).splitlines()

    assert lines[1:] == ["  使った費用 24.0 円", "  推薦が全て失敗したので集計していない"]


def run(name: str, scored: int, unrelated: float, std: float, **config: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {key: spread(0.5, 0.0) for key, _, _ in METRICS}
    summary |= {
        "trials": 30,
        "failures": 0,
        "complete_repeats": scored,
        "scored_repeats": scored,
        "unrelated": spread(unrelated, std),
        "overlap": 0.6,
        "core_overlap": 0.7,
        "yen_per_plan": 1.5,
        "seconds": {"total": 12.0},
    }
    return document(summary) | {"label": name, "config": {"repeats": 3, **config}}


def line_of(lines: list[str], start: str) -> str:
    return next(line for line in lines if line.startswith(start))


def test_compare_tells_whether_a_difference_is_larger_than_the_spread() -> None:
    lines = compare(run("before", 3, 0.20, 0.02), run("after", 3, 0.10, 0.03)).splitlines()

    unrelated = line_of(lines, "  選んだ科目のうち関係なし")
    assert "差 -10 ポイント" in unrelated
    assert unrelated.endswith("揺れより大きい")
    assert line_of(lines, "  中心の適合率").endswith("揺れの範囲")


def test_compare_does_not_judge_the_spread_of_a_run_scored_from_one_repeat() -> None:
    lines = compare(run("before", 1, 0.20, 0.0), run("after", 3, 0.10, 0.03)).splitlines()

    assert line_of(lines, "  選んだ科目のうち関係なし").endswith("、-")
    assert "  before: 推薦 30 回、失敗 0 回、全職業がそろった回 1、採点した回 1" in lines


def test_compare_lists_the_settings_that_differ_but_not_the_budget() -> None:
    before = run("before", 3, 0.2, 0.0, selection_model="gpt-5.4-nano", budget=100)
    after = run("after", 3, 0.2, 0.0, selection_model="gpt-5.4-mini", budget=50)

    lines = compare(before, after).splitlines()

    assert "  設定の違い: selection_model gpt-5.4-nano → gpt-5.4-mini" in lines


def test_compare_shows_a_metric_an_older_run_lacks_without_a_difference() -> None:
    before = run("before", 3, 0.2, 0.0)
    del before["summary"]["candidate_recall"]

    lines = compare(before, run("after", 3, 0.2, 0.0)).splitlines()

    assert line_of(lines, "  選び直しに渡した候補の再現率").endswith(": - → 50% ± 0(50%〜50%)")
