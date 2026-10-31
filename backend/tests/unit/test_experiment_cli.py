import argparse
import json
import math
from collections.abc import Iterator, Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.messages import HumanMessage

from app.application.analyze_experiment import (
    PLACEMENTS,
    CourseTally,
    ExperimentAnalysis,
    Fate,
    ReadingLoss,
)
from app.application.compare_experiments import MIN_OCCUPATIONS, Change, Comparison, Interval
from app.application.compare_experiments import OVERLAPS as MEASURED_OVERLAPS
from app.application.evaluate_search import EvaluationCase, EvaluationDataset
from app.application.evaluate_selection import (
    ExpectedCourse,
    Judgment,
    Pick,
    SelectionResult,
    UnlinkedPick,
)
from app.application.ports import TokenUsage
from app.application.run_experiment import METRICS as MEASURED_METRICS
from app.application.run_experiment import (
    ExperimentSummary,
    FailedTrial,
    Side,
    Spread,
    StageSeconds,
    Trial,
    summarize,
)
from app.application.search_courses import SearchError
from app.domain.course import UNIVERSITY_TIME
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import (
    CourseChoice,
    Recommendation,
    RecommendedCourse,
    Relevance,
)
from app.infrastructure.llm.openai_course_selector import INSTRUCTIONS
from app.infrastructure.llm.usage_meter import LangChainUsageMeter
from app.presentation.cli import experiment as experiment_cli
from app.presentation.cli.experiment import (
    HELDOUT_RUNS,
    METRICS,
    OVERLAPS,
    RUNS,
    Collection,
    arguments,
    collect,
    compare,
    main,
    pair_documents,
    ran_interleaved,
    render,
    render_analysis,
    results_directory,
    scorecard,
    setting,
    summary_document,
    trial_document,
    trial_instructions,
    unpriced,
    with_unrecorded,
    yen,
)
from app.presentation.cli.records import digest, label
from tests.fakes import chat_answering, courses_ranked_by

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

    def __iter__(self) -> Iterator[tuple[Side | None, Trial | FailedTrial]]:
        for outcome in self._outcomes:
            if isinstance(outcome, BaseException):
                raise outcome
            for model, tokens in outcome.usage.items():
                self._usage[model] = self._usage[model] + tokens if model in self._usage else tokens
            yield None, outcome

    def spent(self) -> dict[str, TokenUsage]:
        return dict(self._usage)


def test_collect_stops_before_the_next_recommendation_once_the_budget_is_spent() -> None:
    paid = Paid([succeeded(1), succeeded(2), succeeded(3)])

    collection = collect(iter(paid), 3, 50, paid.spent)

    assert len(collection.outcomes) == 2
    assert (collection.stopped, collection.over_budget) == ("費用の上限 50 円に達した", True)


def test_collect_checks_the_budget_only_between_pairs_when_given_a_unit_of_two() -> None:
    paid = Paid([succeeded(1), succeeded(1), succeeded(2), succeeded(2)])

    collection = collect(iter(paid), 4, 20, paid.spent, unit=2)

    assert len(collection.outcomes) == 2
    assert (collection.stopped, collection.over_budget) == ("費用の上限 20 円に達した", True)


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


def test_collect_counts_failures_in_a_row_for_each_side_of_a_pair() -> None:
    pairs: list[tuple[Side | None, Trial | FailedTrial]] = [
        (Side.BEFORE, succeeded(1)),
        (Side.AFTER, failed(1)),
        (Side.AFTER, failed(1)),
        (Side.BEFORE, succeeded(1)),
        (Side.BEFORE, succeeded(2)),
        (Side.AFTER, failed(2)),
        (Side.AFTER, succeeded(2)),
    ]

    collection = collect(iter(pairs), 8, 1000, dict, unit=2)

    assert len(collection.outcomes) == 6
    assert collection.stopped == "後の推薦が 3 回続けて失敗した"


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

    assert collection.of(None) == [succeeded(1)]
    assert (collection.stopped, collection.over_budget) == (stopped, False)


def test_collect_shows_and_keeps_the_side_each_recommendation_ran_for(
    capsys: pytest.CaptureFixture[str],
) -> None:
    pairs: list[tuple[Side | None, Trial | FailedTrial]] = [
        (Side.BEFORE, succeeded(1)),
        (Side.AFTER, failed(1)),
        (Side.AFTER, succeeded(2)),
    ]

    collection = collect(iter(pairs), 4, 1000, dict)

    assert [line.split("(")[0] for line in capsys.readouterr().err.splitlines()] == [
        "1/4 前 職業",
        "2/4 後 職業",
        "3/4 後 職業",
    ]
    assert collection.of(Side.BEFORE) == [succeeded(1)]
    assert collection.of(Side.AFTER) == [failed(1), succeeded(2)]
    assert collection.of(None) == []


def test_collect_leaves_out_the_failure_reasons_of_the_heldout_set(
    capsys: pytest.CaptureFixture[str],
) -> None:
    hidden = FailedTrial("職業", 1, "候補に無い科目が選ばれています: 科目A", THIRTY_YEN)

    collect(iter([(None, hidden)]), 1, 1000, dict, heldout=True)

    shown = capsys.readouterr().err
    assert "失敗: 確かめ用なので理由は出さない" in shown
    assert "科目A" not in shown


def test_collect_leaves_out_why_a_heldout_run_stopped(capsys: pytest.CaptureFixture[str]) -> None:
    paid = Paid([succeeded(1), RuntimeError("科目A を選んだ答えが壊れている")])

    collection = collect(iter(paid), 2, 1000, paid.spent, heldout=True)

    assert collection.stopped == "思わぬ失敗で止まった: 確かめ用なので理由は出さない"
    assert "科目A" not in capsys.readouterr().err


@pytest.mark.parametrize(
    ("heldout", "out", "chosen"),
    [
        (False, None, RUNS),
        (False, Path("elsewhere"), Path("elsewhere")),
        (True, None, HELDOUT_RUNS),
    ],
    ids=["development", "development-out", "heldout"],
)
def test_heldout_results_go_outside_the_committed_runs(
    heldout: bool, out: Path | None, chosen: Path
) -> None:
    case = EvaluationCase("職業", ("甲", "乙", "丙"), ("科目A",))

    assert results_directory(out, EvaluationDataset(2026, "情", (case,), heldout)) == chosen


@pytest.mark.parametrize("out", [Path("elsewhere"), RUNS], ids=["anywhere", "committed-runs"])
def test_heldout_results_refuse_any_other_directory(out: Path) -> None:
    case = EvaluationCase("職業", ("甲", "乙", "丙"), ("科目A",))

    with pytest.raises(SystemExit, match="確かめ用の結果は"):
        results_directory(out, EvaluationDataset(2026, "情", (case,), heldout=True))


@pytest.mark.parametrize(
    ("text", "parsed"),
    [
        ("SELECTION_VOTES=1", ("SELECTION_VOTES", "1")),
        ("SELECTION_MIN_VOTES=1", ("SELECTION_MIN_VOTES", "1")),
        ("OCCUPATION_READING_CACHE_SIZE=0", ("OCCUPATION_READING_CACHE_SIZE", "0")),
        ("CHAT_MODEL=gpt-5.4-nano", ("CHAT_MODEL", "gpt-5.4-nano")),
        (
            "EMBEDDING_MODEL=text-embedding-3-small",
            ("EMBEDDING_MODEL", "text-embedding-3-small"),
        ),
        ("SEARCH_BY_SKILL=false", ("SEARCH_BY_SKILL", "false")),
        ("SELECTION_PROMPT=prompt.txt", ("SELECTION_PROMPT", "prompt.txt")),
    ],
)
def test_a_pair_setting_names_a_setting_on_the_recommendation_path(
    text: str, parsed: tuple[str, str]
) -> None:
    assert setting(text) == parsed


@pytest.mark.parametrize(
    "text",
    [
        "SELECTION_VOTES",
        "selection_votes=1",
        "DATABASE_URL=postgresql://other",
        "SELECTION_MODEL=",
        "EMBEDDING_DIMENSIONS=3072",
    ],
    ids=["no-value", "lowercase", "database", "empty", "dimensions"],
)
def test_a_pair_setting_off_the_recommendation_path_is_refused(text: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="替えられるのは"):
        setting(text)


def test_each_side_of_a_pair_keeps_its_own_trials_cost_and_partner() -> None:
    collection = Collection(
        [
            (Side.BEFORE, replace(picking("職業", 0), repeat=1)),
            (Side.AFTER, failed(1)),
            (Side.AFTER, replace(picking("職業", 1), repeat=2)),
            (Side.BEFORE, replace(picking("職業", 0), repeat=2)),
            (Side.BEFORE, replace(picking("職業", 0), repeat=3)),
        ],
        "中断した",
        False,
    )

    documents = pair_documents(
        "votes",
        datetime(2026, 10, 23, 18, 0, tzinfo=UNIVERSITY_TIME),
        "abc1234",
        collection,
        151.0,
        {Side.BEFORE: {"selection_votes": 1}, Side.AFTER: {"selection_votes": 3}},
        {Side.BEFORE: "votes-before.json", Side.AFTER: "votes-after.json"},
        (EvaluationCase("職業", ("甲", "乙", "丙"), ("科目A",)),),
    )

    before, after = documents[Side.BEFORE], documents[Side.AFTER]
    assert (before["label"], after["label"]) == ("votes-before", "votes-after")
    assert [trial["repeat"] for trial in before["trials"]] == [1, 2, 3]
    assert ["failure" in trial for trial in after["trials"]] == [True, False]
    assert (before["spent_yen"], after["spent_yen"]) == (pytest.approx(90.0), pytest.approx(60.0))
    assert (before["config"], after["config"]) == ({"selection_votes": 1}, {"selection_votes": 3})
    assert before["pair"] == {
        "label": "votes",
        "side": "before",
        "partner": "votes-after.json",
        "spent_yen": 151.0,
    }
    assert after["pair"]["partner"] == "votes-before.json"
    assert before["stopped"] == after["stopped"] == "中断した"
    assert ran_interleaved(before, after)


def test_a_trial_prompt_is_read_without_the_surrounding_blanks(tmp_path: Path) -> None:
    prompt = tmp_path / "selection.txt"
    prompt.write_text("試す指示文\n", encoding="utf-8")

    assert trial_instructions(str(prompt)) == "試す指示文"
    assert trial_instructions(None) == INSTRUCTIONS


@pytest.mark.parametrize(
    ("kind", "message"),
    [
        ("missing", "SELECTION_PROMPT を読めません"),
        ("directory", "SELECTION_PROMPT を読めません"),
        ("blank", "SELECTION_PROMPT の文面が空です"),
        ("placeholder", "組み込みの文面の書き方"),
        ("line-join", "組み込みの文面の書き方"),
        ("escaped-brace", "組み込みの文面の書き方"),
        ("lowercase-placeholder", "組み込みの文面の書き方"),
    ],
)
def test_a_trial_prompt_that_cannot_be_used_is_refused(
    tmp_path: Path, kind: str, message: str
) -> None:
    prompt = tmp_path / "selection.txt"
    texts = {
        "blank": " \n",
        "placeholder": "理由は {REASON_LIMIT} 字以内",
        "line-join": "前の行\\\n次の行",
        "escaped-brace": '例 {{"name": 1}}',
        "lowercase-placeholder": "{limit} 字以内",
    }
    if kind == "directory":
        prompt.mkdir()
    if kind in texts:
        prompt.write_text(texts[kind], encoding="utf-8")

    with pytest.raises(SystemExit, match=message):
        trial_instructions(str(prompt))


def test_pair_builds_each_side_with_the_selection_prompt_it_was_given(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prompt = tmp_path / "selection.txt"
    prompt.write_text("試す指示文", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    given: list[str] = []

    class Stopped(Exception):
        pass

    class Unrun:
        def trials(self, *args: object) -> None:
            raise Stopped

    def built(*args: object) -> Unrun:
        given.append(str(args[-1]))
        return Unrun()

    monkeypatch.setattr(experiment_cli, "_experiment", built)
    monkeypatch.setattr(experiment_cli, "database_engine", lambda settings: None)

    with pytest.raises(Stopped):
        main(["pair", "--label", "prompt", "--after", f"SELECTION_PROMPT={prompt}"])

    assert given == [INSTRUCTIONS, "試す指示文"]


def test_pair_reads_the_settings_of_every_before_and_after_flag() -> None:
    args = arguments(
        [
            "pair",
            "--label",
            "votes",
            "--before",
            "CHAT_MODEL=gpt-5.4-nano",
            "--before",
            "SELECTION_VOTES=1",
            "SELECTION_CANDIDATE_LIMIT=30",
            "--after",
            "SELECTION_VOTES=3",
        ]
    )

    assert args.before == [
        ("CHAT_MODEL", "gpt-5.4-nano"),
        ("SELECTION_VOTES", "1"),
        ("SELECTION_CANDIDATE_LIMIT", "30"),
    ]
    assert args.after == [("SELECTION_VOTES", "3")]
    assert args.budget == 200


@pytest.mark.parametrize("override", ["CHAT_MODEL=gpt-5.4-nano", "OCCUPATION_READING_CACHE_SIZE=0"])
def test_pair_refuses_reading_settings_when_the_skills_are_handwritten(
    override: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["pair", "--label", "skills", "--profiles", "handwritten", "--after", override])

    assert stopped.value.code == 2
    assert "職業の読み取りを使わない" in capsys.readouterr().err


@pytest.mark.parametrize(
    "flags",
    [
        ["--after", "SELECTION_VOTES=1", "SELECTION_VOTES=3"],
        ["--before", "SELECTION_VOTES=1", "--before", "SELECTION_VOTES=3"],
    ],
    ids=["one-flag", "two-flags"],
)
def test_pair_refuses_the_same_setting_twice_on_one_side(
    flags: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as stopped:
        main(["pair", "--label", "votes", *flags])

    assert stopped.value.code == 2
    assert "同じ設定は 1 回だけ" in capsys.readouterr().err


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
            "occupation_reading_cache_size": 0,
            "selection_model": "gpt-5.4-nano",
            "selection_votes": 1,
            "selection_vote_delay_seconds": 0.0,
            "embedding_model": "text-embedding-3-small",
            "search_by_skill": False,
            "candidate_limit": 30,
        },
        "summary": summary,
        "trials": [{"occupation": "職業", "repeat": 1, "failure": "失敗"}],
    }


def test_the_summary_document_names_every_metric_it_shows() -> None:
    value = Spread(0.5, 0.1, 0.4, 0.6)
    summary = ExperimentSummary(
        trials=2,
        failures=0,
        complete_repeats=2,
        scored_repeats=2,
        metrics={key: value for key, _, _ in METRICS} | {"core_precision": None},
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


def test_a_side_stopped_before_it_ran_anything_says_so() -> None:
    lines = render(document(None) | {"trials": []}).splitlines()

    assert lines[-1] == "  この側の推薦を流す前に止まったので集計していない"


def test_one_side_of_a_pair_shows_its_own_cost_beside_the_cost_of_the_pair() -> None:
    side = document(None) | {"pair": {"label": "votes", "side": "before", "spent_yen": 50.0}}

    assert render(side).splitlines()[1] == (
        "  使った費用 24.0 円(この側の推薦の分。交互に流した組 votes の 2 つで 50.0 円、"
        "途中で止めた推薦の分を含む)"
    )


def run(name: str, **config: Any) -> dict[str, Any]:
    summary = {
        "trials": 30,
        "failures": 0,
        "complete_repeats": 3,
        "scored_repeats": 3,
        "yen_per_plan": 1.5,
        "seconds": {"total": 12.0},
    }
    return document(summary) | {
        "label": name,
        "config": {"occupations": 10, "repeats": 3, **config},
    }


def line_of(lines: list[str], start: str) -> str:
    return next(line for line in lines if line.startswith(start))


def measured(occupations: int, changes: dict[str, Change]) -> Comparison:
    unknown = Change(None, None, None, None)
    return Comparison(
        occupations,
        (3, 3),
        {key: changes.get(key, unknown) for key, _, _ in (*METRICS, *OVERLAPS)},
    )


def paired(name: str, side: str, **pair: str) -> dict[str, Any]:
    return run(name) | {"pair": {"label": "votes", "side": side, "partner": "other.json"} | pair}


NOTHING_MEASURED = measured(MIN_OCCUPATIONS, {})


def test_the_cli_shows_every_metric_and_overlap_the_comparison_measures() -> None:
    assert [key for key, _, _ in METRICS] == list(MEASURED_METRICS)
    assert [key for key, _, _ in OVERLAPS] == list(MEASURED_OVERLAPS)


def test_compare_decides_each_change_by_its_p_value_and_shows_the_interval_beside_it() -> None:
    comparison = measured(
        10,
        {
            "candidate_recall": Change(1.0, 0.9, Interval(-0.2, 0.0), None),
            "unrelated": Change(0.2, 0.1, Interval(-0.15, -0.05), 0.0004),
            "core_precision": Change(0.5, math.nextafter(0.5, 0.0), Interval(-0.05, 0.05), 1.0),
            "expected_as_core": Change(0.8, 0.7, Interval(-0.2, -0.01), 0.06),
            "overlap": Change(0.6, 0.6, Interval(-0.1, 0.1), 0.5),
            "cores": Change(5.0, 4.4, None, 0.03),
            "foundations": Change(None, 3.9, None, None),
        },
    )

    lines = compare(run("before"), run("after"), comparison).splitlines()

    assert lines[3:] == [
        "  交互に流した組でないので、差に流した時刻の揺れも入る(交互に流すのは pair)",
        "  両方にそろった 10 職業で比べる。差ありは職業ごとに前と後を入れ替える並べ替え検定"
        "(10,000 通り)で p < 0.05、区間は 95% 信頼区間(職業を選び直すブートストラップ 10,000 回)",
        "  区間なしの指標は、職業を選び直すと割合を出せない組がある",
        "  判定なしの指標は、前と後を入れ替えると割合を出せない組がある",
        "  検索の再現率 @10: - → -",
        "  検索の再現率 @20: - → -",
        "  選び直しに渡した候補の再現率: 100.0% → 90.0%、差 -10.0 ポイント(区間 -20.0〜+0.0)、"
        "判定なし",
        "  中心の適合率: 50.0% → 50.0%、差 +0.0 ポイント(区間 -5.0〜+5.0、p = 1.000)、"
        "はっきりしない",
        "  期待する科目を中心に選んだ割合: 80.0% → 70.0%、差 -10.0 ポイント"
        "(区間 -20.0〜-1.0、p = 0.060)、はっきりしない",
        "  選んだ科目のうち関係なし: 20.0% → 10.0%、差 -10.0 ポイント"
        "(区間 -15.0〜-5.0、p < 0.001)、差あり",
        "  1 職業に選んだ中心: 5.00 → 4.40、差 -0.60(区間なし、p = 0.030)、差あり",
        "  1 職業に選んだ土台: - → 3.90",
        "  揺れ(選んだ科目の重なり): 0.60 → 0.60、差 +0.00(区間 -0.10〜+0.10、p = 0.500)、"
        "はっきりしない",
        "  揺れ(中心の重なり): - → -",
        "  1 回の推薦あたりの費用: 1.50 円 → 1.50 円",
        "  1 回の推薦の時間: 12.0 秒 → 12.0 秒",
    ]


def test_compare_gives_no_interval_or_verdict_for_fewer_occupations_than_were_checked() -> None:
    comparison = measured(7, {"unrelated": Change(0.2, 0.1, None, None)})

    lines = compare(run("before"), run("after"), comparison).splitlines()

    assert lines[4:6] == [
        "  両方にそろった 7 職業で比べる。10 職業に満たないので区間と判定は出さない",
        "  前と後の値は、それぞれの集計(before 10 職業 × 3 回、after 10 職業 × 3 回)"
        "と違うことがある",
    ]
    assert "  選んだ科目のうち関係なし: 20.0% → 10.0%、差 -10.0 ポイント、区間と判定なし" in lines


@pytest.mark.parametrize(
    ("repeats", "note"),
    [
        ((2, 2), "  前と後の両方で採点した 2 回だけで比べる"),
        (
            (3, 1),
            "  採点した回の数が違う(3 回と 1 回)ので、重なり以外は前と後を入れ替えられず判定なし",
        ),
    ],
    ids=["aligned-pair", "different-counts"],
)
def test_compare_says_when_the_repeats_it_compares_differ_from_the_runs(
    repeats: tuple[int, int], note: str
) -> None:
    comparison = Comparison(10, repeats, NOTHING_MEASURED.changes)

    lines = compare(run("before"), run("after"), comparison).splitlines()

    assert note in lines
    assert line_of(lines, "  前と後の値は、それぞれの集計")


@pytest.mark.parametrize(
    ("p_value", "shown"),
    [
        (500 / 10_001, "p = 0.049)、差あり"),
        (501 / 10_001, "p = 0.050)、はっきりしない"),
        (0.03, "p = 0.030)、差あり"),
    ],
    ids=["just-below", "just-above", "exact-decimal"],
)
def test_compare_cuts_the_p_value_down_so_it_never_reads_against_the_verdict(
    p_value: float, shown: str
) -> None:
    comparison = measured(10, {"unrelated": Change(0.2, 0.1, Interval(-0.15, -0.05), p_value)})

    lines = compare(run("before"), run("after"), comparison).splitlines()

    assert line_of(lines, "  選んだ科目のうち関係なし").endswith(shown)


def test_compare_does_not_warn_about_the_time_for_the_two_sides_of_one_pair() -> None:
    lines = compare(
        paired("votes-before", "before"), paired("votes-after", "after"), NOTHING_MEASURED
    ).splitlines()

    assert not any(line.startswith("  交互に流した組でない") for line in lines)


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (paired("a", "before"), paired("b", "before")),
        (paired("a", "before"), paired("b", "after", label="other")),
        (paired("a", "before"), paired("b", "after") | {"created": "2026-10-24T04:00:00+09:00"}),
        (paired("a", "before"), run("b")),
        (run("a") | {"pair": {"side": "before"}}, run("b") | {"pair": {"side": "after"}}),
    ],
    ids=["same-side", "other-pair", "other-time", "single-run", "no-label"],
)
def test_compare_warns_about_the_time_unless_both_runs_are_one_pair(
    before: dict[str, Any], after: dict[str, Any]
) -> None:
    lines = compare(before, after, NOTHING_MEASURED).splitlines()

    assert "  交互に流した組でないので、差に流した時刻の揺れも入る(交互に流すのは pair)" in lines


def test_compare_lists_the_settings_that_differ_but_not_the_budget() -> None:
    before = run("before", selection_model="gpt-5.4-nano", budget=100)
    after = run("after", selection_model="gpt-5.4-mini", budget=50)

    lines = compare(before, after, NOTHING_MEASURED).splitlines()

    assert "  設定の違い: selection_model gpt-5.4-nano → gpt-5.4-mini" in lines
    assert not any(line.startswith("  評価データか判定が違う") for line in lines)


@pytest.mark.parametrize("key", ["dataset", "judgments"])
def test_compare_warns_that_a_regraded_run_mixes_in_the_new_labels(key: str) -> None:
    before = run("before", **{key: "aaaa1111"})
    after = run("after", **{key: "bbbb2222"})

    lines = compare(before, after, NOTHING_MEASURED).splitlines()

    assert "  評価データか判定が違うので、差には正解の付け直しの分も入る" in lines


def test_compare_reads_a_run_from_before_votes_as_a_single_vote() -> None:
    before = run("before")
    after = run("after", selection_votes=3)

    lines = compare(before, after, NOTHING_MEASURED).splitlines()

    assert "  設定の違い: selection_min_votes 1 → 2、selection_votes 1 → 3" in lines
    single = compare(
        before,
        run("after", selection_votes=1, selection_vote_delay_seconds=0.0),
        NOTHING_MEASURED,
    ).splitlines()
    assert not any(line.startswith("  設定の違い") for line in single)


def test_compare_reads_a_run_from_before_the_skill_search_as_one_query() -> None:
    lines = compare(
        run("before"), run("after", search_by_skill=True), NOTHING_MEASURED
    ).splitlines()

    assert "  設定の違い: search_by_skill False → True" in lines


def test_the_heading_names_the_embedding_model_and_how_the_search_ranks() -> None:
    one_query = render(document(None)).splitlines()[0]
    by_skill = document(None)
    by_skill["config"] = by_skill["config"] | {
        "embedding_model": "text-embedding-3-large",
        "search_by_skill": True,
    }

    assert "埋め込み text-embedding-3-small、検索 クエリ 1 つ、" in one_query
    assert "埋め込み text-embedding-3-large、検索 スキルごと、" in render(by_skill).splitlines()[0]


def test_the_raw_output_reads_back_into_the_scorecard_it_was_written_from() -> None:
    outcome = Trial(
        "職業",
        2,
        Recommendation(
            PROFILE,
            (
                RecommendedCourse("科目A", "10000", Relevance.CORE, "理由A"),
                RecommendedCourse("科目B", "10001", Relevance.FOUNDATION, "理由B", "科目A"),
            ),
            ("科目A", "科目B", "科目C", "科目D"),
            (CourseChoice("科目C", Relevance.FOUNDATION, "理由C", "科目D"),),
        ),
        SelectionResult(
            "職業",
            (
                Pick("科目A", Relevance.CORE, Judgment.EXPECTED),
                Pick("科目B", Relevance.FOUNDATION, Judgment.UNRELATED),
            ),
            (
                ExpectedCourse("科目A", Relevance.CORE, True, False),
                ExpectedCourse("科目E", None, False, False),
            ),
            (UnlinkedPick("科目C", "科目D", Judgment.FOUNDATION),),
        ),
        THIRTY_YEN,
        StageSeconds(1.0, 1.0, 1.0),
    )

    assert scorecard(trial_document(outcome)) == outcome.scorecard


def picking(occupation: str, unrelated: int) -> Trial:
    names = ("科目A", *(f"科目{number}" for number in range(unrelated)))
    return Trial(
        occupation,
        1,
        Recommendation(
            PROFILE,
            tuple(RecommendedCourse(name, "10000", Relevance.CORE, "理由") for name in names),
            names,
        ),
        SelectionResult(
            occupation,
            tuple(
                Pick(
                    name,
                    Relevance.CORE,
                    Judgment.EXPECTED if name == "科目A" else Judgment.UNRELATED,
                )
                for name in names
            ),
            (ExpectedCourse("科目A", Relevance.CORE, True, False),),
            (),
        ),
        THIRTY_YEN,
        StageSeconds(1.0, 1.0, 1.0),
    )


def saved_run(
    directory: Path, name: str, unrelated: Sequence[int], repeat: int = 1, **extra: Any
) -> Path:
    cases = tuple(
        EvaluationCase(f"職業{index}", ("甲", "乙", "丙"), ("科目A",)) for index in range(10)
    )
    outcomes: list[Trial | FailedTrial] = [
        replace(picking(case.occupation, count), repeat=repeat)
        for case, count in zip(cases, unrelated, strict=True)
    ]
    outcomes.append(FailedTrial("職業0", repeat + 1, "失敗", THIRTY_YEN))
    summary = summarize(outcomes, cases)
    assert summary is not None
    written = (
        document(summary_document(summary))
        | {"label": name, "trials": [trial_document(outcome) for outcome in outcomes]}
        | extra
    )
    path = directory / f"{name}.json"
    path.write_text(json.dumps(written, ensure_ascii=False), encoding="utf-8")
    return path


def test_compare_pairs_the_occupations_of_two_saved_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = saved_run(tmp_path, "before", (1, 2) * 5)
    after = saved_run(tmp_path, "after", (0,) * 10)

    main(["compare", str(before), str(after)])

    lines = capsys.readouterr().out.splitlines()
    assert line_of(lines, "  両方にそろった 10 職業で比べる。差ありは職業ごとに")
    unrelated = line_of(lines, "  選んだ科目のうち関係なし")
    assert unrelated.startswith(
        "  選んだ科目のうち関係なし: 60.0% → 0.0%、差 -60.0 ポイント(区間 -"
    )
    assert unrelated.endswith(")、差あり") and "、p = 0.00" in unrelated
    assert (
        "  期待する科目を中心に選んだ割合: 100.0% → 100.0%、差 +0.0 ポイント"
        "(区間 +0.0〜+0.0、p = 1.000)、はっきりしない"
    ) in lines


def test_compare_refuses_the_two_sides_of_a_pair_that_share_no_scored_repeat(
    tmp_path: Path,
) -> None:
    pair = {"label": "votes", "partner": "other.json"}
    before = saved_run(tmp_path, "votes-before", (0,) * 10, pair=pair | {"side": "before"})
    after = saved_run(tmp_path, "votes-after", (0,) * 10, repeat=2, pair=pair | {"side": "after"})

    with pytest.raises(SystemExit, match="前と後の両方で採点した回が無い"):
        main(["compare", str(before), str(after)])


@pytest.mark.parametrize(
    ("replacement", "reason"),
    [
        (
            {"courses": [{"name": "科目A", "relevance": "central", "judgment": "expected"}]},
            "'central' is not a valid Relevance",
        ),
        ({"expected": []}, "職業0: 期待する科目がありません"),
    ],
    ids=["unknown-relevance", "no-expected-course"],
)
def test_compare_refuses_a_saved_run_whose_recommendations_cannot_be_scored(
    tmp_path: Path, replacement: dict[str, Any], reason: str
) -> None:
    before = saved_run(tmp_path, "before", (1,) * 10)
    broken = json.loads(before.read_text(encoding="utf-8"))
    broken["trials"][0] |= replacement
    before.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SystemExit) as stopped:
        main(["compare", str(before), str(saved_run(tmp_path, "after", (0,) * 10))])

    assert str(stopped.value.code).startswith("実験の結果の推薦を読めません: ValueError(")
    assert reason in str(stopped.value.code)


def test_the_analysis_shows_each_fate_with_its_share_and_the_readings_behind_the_losses() -> None:
    reading = "読んだ職業(前提: 前提) / スキル: 甲 / 乙"
    readings = {
        ("職業", 1): reading,
        ("職業", 2): reading,
        ("職業", 3): "職業 / スキル: 丙",
        ("職業", 4): "使わない読み取り",
    }
    analysis = ExperimentAnalysis(
        {fate: 0 for fate in Fate} | {Fate.CORE: 3, Fate.READING: 1},
        {placement: {judgment: 0 for judgment in Judgment} for placement in PLACEMENTS},
        (CourseTally("科目B", {Fate.READING: 2, Fate.SKIPPED: 1}, 1),),
        (CourseTally("科目C", {Fate.FOUNDATION: 1, Fate.CORE: 2}, 2),),
        (ReadingLoss("職業", (1, 2, 3), {"科目B": 2, "科目D": 1}),),
    )
    dataset = EvaluationDataset(
        2026, "情", (EvaluationCase("職業", ("甲", "乙", "丙"), ("科目B",)),)
    )

    lines = render_analysis(["見出し"], readings, analysis, dataset).splitlines()

    assert "  中心に選んだ 3(75.0%)" in lines
    assert "  候補に無く、手書きのスキルなら入る(読み取りで落とした) 1(25.0%)" in lines
    assert "  科目B 3 回(1 職業): 選び直し 1、読み取り 2" in lines
    assert "  科目C 3 回(2 職業): 中心 2、土台 1" in lines
    assert lines[0] == "見出し"
    assert lines[-4:] == [
        "  職業 3 件: 科目B 2、科目D 1",
        "    1、2 回目の読み取り: 読んだ職業(前提: 前提) / スキル: 甲 / 乙",
        "    3 回目の読み取り: 職業 / スキル: 丙",
        "    手書きのスキル: 甲 / 乙 / 丙",
    ]


def written_dataset(tmp_path: Path, heldout: bool = False) -> Path:
    path = tmp_path / "occupations.json"
    path.write_text(
        json.dumps(
            {
                "year": 2026,
                "department": "情",
                "heldout": heldout,
                "occupations": [
                    {"name": "職業", "skills": ["甲", "乙", "丙"], "expected": {"科目B": "理由"}}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def written_run(tmp_path: Path, dataset: Path, **changed: Any) -> Path:
    trial = {
        "occupation": "職業",
        "repeat": 1,
        "interpretation": "読んだ職業",
        "assumption": "前提",
        "skills": ["丁"],
        "candidates": ["科目A"],
        "courses": [
            {
                "name": "科目A",
                "relevance": "core",
                "judgment": "unrelated",
                "reason": "理由",
                "prerequisite_for": None,
            }
        ],
        "unlinked": [],
        "expected": [{"name": "科目B", "picked": None, "searched": False, "unlinked": False}],
    }
    content = run(
        "analyzed",
        occupations=1,
        profiles="analyzed",
        dataset=digest(dataset.read_bytes()),
        embedding_model="text-embedding-3-large",
        search_by_skill=True,
        candidate_limit=2,
    ) | {"trials": [trial]}
    content = content | {key: value for key, value in changed.items() if key != "config"}
    content["config"] |= changed.get("config", {})
    path = tmp_path / "run.json"
    path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def search_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
    monkeypatch.setenv("SEARCH_BY_SKILL", "true")
    monkeypatch.setenv("SELECTION_CANDIDATE_LIMIT", "2")


@pytest.mark.usefixtures("search_settings")
def test_analyze_traces_a_course_the_handwritten_skills_would_find_to_the_reading(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8, "科目C": 0.7})
    disposed: list[bool] = []
    engine = SimpleNamespace(dispose=lambda: disposed.append(True))
    monkeypatch.setattr(experiment_cli, "database_engine", lambda settings: engine)
    monkeypatch.setattr(experiment_cli, "search_courses", lambda settings, engine: search)
    dataset = written_dataset(tmp_path)

    main(["analyze", str(written_run(tmp_path, dataset)), "--dataset", str(dataset)])

    assert disposed == [True]
    lines = capsys.readouterr().out.splitlines()
    assert "  候補に無く、手書きのスキルなら入る(読み取りで落とした) 1(100.0%)" in lines
    assert "  科目A 1 回(1 職業): 中心 1" in lines
    assert lines[-3:] == [
        "  職業 1 件: 科目B 1",
        "    1 回目の読み取り: 読んだ職業(前提: 前提) / スキル: 丁",
        "    手書きのスキル: 甲 / 乙 / 丙",
    ]


def test_analyze_refuses_the_heldout_set_whose_courses_must_not_be_seen(tmp_path: Path) -> None:
    dataset = written_dataset(tmp_path, heldout=True)

    with pytest.raises(SystemExit, match="確かめ用の評価データ"):
        main(["analyze", str(written_run(tmp_path, dataset)), "--dataset", str(dataset)])


def test_analyze_refuses_a_run_graded_with_another_dataset(tmp_path: Path) -> None:
    dataset = written_dataset(tmp_path)
    path = written_run(tmp_path, dataset, config={"dataset": "00000000"})

    with pytest.raises(SystemExit, match="別の評価データ"):
        main(["analyze", str(path), "--dataset", str(dataset)])


@pytest.mark.usefixtures("search_settings")
def test_analyze_refuses_to_search_differently_from_the_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
    dataset = written_dataset(tmp_path)

    with pytest.raises(
        SystemExit,
        match="embedding_model が結果は text-embedding-3-large、今は text-embedding-3-small",
    ):
        main(["analyze", str(written_run(tmp_path, dataset)), "--dataset", str(dataset)])


def test_analyze_refuses_a_run_without_scores(tmp_path: Path) -> None:
    dataset = written_dataset(tmp_path)

    with pytest.raises(SystemExit, match="集計の無い結果"):
        main(
            [
                "analyze",
                str(written_run(tmp_path, dataset, summary=None)),
                "--dataset",
                str(dataset),
            ]
        )


def test_analyze_refuses_a_run_that_used_the_handwritten_skills_instead_of_a_reading(
    tmp_path: Path,
) -> None:
    dataset = written_dataset(tmp_path)
    path = written_run(tmp_path, dataset, config={"profiles": "handwritten"})

    with pytest.raises(SystemExit, match="読み取りを通っていない"):
        main(["analyze", str(path), "--dataset", str(dataset)])


def test_analyze_says_it_cannot_read_a_file_that_is_not_a_run(tmp_path: Path) -> None:
    dataset = written_dataset(tmp_path)

    with pytest.raises(SystemExit, match="実験の結果を読めません: KeyError"):
        main(["analyze", str(dataset), "--dataset", str(dataset)])


@pytest.mark.usefixtures("search_settings")
def test_analyze_refuses_a_run_missing_a_reading_before_it_searches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def unreached(settings: object) -> None:
        raise AssertionError("検索の前に断るはず")

    monkeypatch.setattr(experiment_cli, "database_engine", unreached)
    dataset = written_dataset(tmp_path)
    path = written_run(tmp_path, dataset)
    content = json.loads(path.read_text(encoding="utf-8"))
    del content["trials"][0]["skills"]
    path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SystemExit, match="実験の結果を読めません: KeyError"):
        main(["analyze", str(path), "--dataset", str(dataset)])


def test_the_heading_names_how_many_votes_keep_a_course_only_when_votes_are_taken() -> None:
    single = document(None)
    voted = document(None)
    voted["config"] = voted["config"] | {"selection_votes": 3, "selection_min_votes": 1}

    assert "選び直し 1 回、" in render(single).splitlines()[0]
    assert "選び直し 3 回(1 票で採る)、" in render(voted).splitlines()[0]


def test_a_result_without_the_kept_votes_reads_as_a_majority_of_its_votes() -> None:
    assert with_unrecorded({"selection_votes": 3})["selection_min_votes"] == 2
    assert with_unrecorded({})["selection_min_votes"] == 1
    assert (
        with_unrecorded({"selection_votes": 3, "selection_min_votes": None})["selection_min_votes"]
        == 2
    )
    assert (
        with_unrecorded({"selection_votes": 3, "selection_min_votes": 1})["selection_min_votes"]
        == 1
    )
