import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from app.application.evaluate_search import EvaluationCase, EvaluationDataset
from app.application.evaluate_selection import Judgment, Judgments
from app.application.measure_calibration import (
    Layout,
    MeasureCalibration,
    OccupationOdds,
    SelectorTrial,
)
from app.application.ports import Classification, ClassificationError, CourseOdds
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse, Relevance
from app.presentation.cli.calibrate import collect, main, render, selector_trials, yen
from app.presentation.cli.records import digest, reserve
from tests.builders import course_section, syllabus
from tests.fakes import FakeCourseRepository

PROFILE = OccupationProfile("職業", "読んだ職業", "前提", ("甲", "乙", "丙"))
DATASET = EvaluationDataset(2026, "情", (EvaluationCase("職業", ("甲", "乙", "丙"), ("科目1",)),))


def run_trial(occupation: str = "職業", repeat: int = 1) -> dict[str, Any]:
    return {
        "occupation": occupation,
        "repeat": repeat,
        "interpretation": "読んだ職業",
        "assumption": "前提",
        "skills": ["甲", "乙", "丙"],
        "candidates": ["科目1", "科目2"],
        "courses": [{"name": "科目2", "relevance": "foundation"}],
    }


def test_a_selector_trial_keeps_the_reading_candidates_and_picks() -> None:
    [read] = selector_trials([run_trial()])

    assert read == SelectorTrial(
        "職業", PROFILE, ("科目1", "科目2"), (("科目2", Relevance.FOUNDATION),)
    )


class Classifier:
    def __init__(self, failing_call: int | None = None) -> None:
        self.calls = 0
        self._failing_call = failing_call

    def classify(
        self, profile: OccupationProfile, candidates: Sequence[CandidateCourse]
    ) -> Classification:
        self.calls += 1
        if self.calls == self._failing_call:
            raise ClassificationError("Jev が 500 を返しました")
        return Classification(
            tuple(CourseOdds(candidate.name, 0.5, 0.3, 0.2) for candidate in candidates),
            1_000_000,
        )


def measure(classifier: Classifier) -> MeasureCalibration:
    repository = FakeCourseRepository(
        (course_section("1"), course_section("2")), (syllabus("1"), syllabus("2"))
    )
    return MeasureCalibration(repository, classifier)


def test_collect_measures_every_layout_in_order_and_adds_up_the_cost() -> None:
    trials = selector_trials([run_trial(), run_trial("別の職業")])

    collected = collect(
        measure(Classifier()), DATASET, trials, (Layout.GROUPED, Layout.SEPARATE), 100
    )

    assert [len(collected.measured[layout]) for layout in Layout] == [2, 2]
    assert collected.spent_yen == pytest.approx(yen(6_000_000))
    assert collected.stopped is None


def test_collect_stops_once_the_budget_is_spent() -> None:
    trials = selector_trials([run_trial(), run_trial("別の職業")])

    collected = collect(measure(Classifier()), DATASET, trials, (Layout.GROUPED,), yen(1_000_000))

    assert len(collected.measured[Layout.GROUPED]) == 1
    assert collected.stopped is not None and "費用の上限" in collected.stopped


def test_collect_does_not_call_a_finished_run_stopped_when_its_last_call_crosses_the_budget() -> (
    None
):
    trials = selector_trials([run_trial(), run_trial("別の職業")])

    collected = collect(measure(Classifier()), DATASET, trials, (Layout.GROUPED,), yen(2_000_000))

    assert len(collected.measured[Layout.GROUPED]) == 2
    assert collected.stopped is None


class Interrupted(Classifier):
    def classify(
        self, profile: OccupationProfile, candidates: Sequence[CandidateCourse]
    ) -> Classification:
        if self.calls == 1:
            raise KeyboardInterrupt
        return super().classify(profile, candidates)


def test_collect_keeps_what_was_measured_when_interrupted() -> None:
    trials = selector_trials([run_trial(), run_trial("別の職業")])

    collected = collect(measure(Interrupted()), DATASET, trials, (Layout.GROUPED,), 100)

    assert [occupation.occupation for occupation in collected.measured[Layout.GROUPED]] == ["職業"]
    assert (collected.stopped, collected.over_budget) == ("中断した", False)


def test_collect_counts_the_calls_made_before_a_one_by_one_occupation_failed() -> None:
    trials = selector_trials([run_trial()])

    collected = collect(
        measure(Classifier(failing_call=2)), DATASET, trials, (Layout.SEPARATE,), 100
    )

    assert collected.measured[Layout.SEPARATE] == []
    assert collected.spent_yen == pytest.approx(yen(1_000_000))


def test_collect_keeps_what_was_measured_when_jev_fails() -> None:
    trials = selector_trials([run_trial(), run_trial("別の職業")])

    collected = collect(
        measure(Classifier(failing_call=2)), DATASET, trials, (Layout.GROUPED,), 100
    )

    assert [occupation.occupation for occupation in collected.measured[Layout.GROUPED]] == ["職業"]
    assert collected.stopped == "Jev が 500 を返しました"


def calibration_document(**changed: Any) -> dict[str, Any]:
    return {
        "label": "jev",
        "created": "2026-10-30T12:00:00+09:00",
        "model": "jev-1.14.0",
        "prompt": "abcd1234",
        "source": {"file": "run.json", "label": "selection", "yen_per_plan": 0.99},
        "repeat": 1,
        "spent_yen": 0.12,
        "stopped": None,
        **changed,
    }


def test_the_report_shows_each_layout_with_its_calibration_and_the_matched_choices() -> None:
    trials = selector_trials([run_trial()])
    measured = {
        Layout.GROUPED: [
            OccupationOdds(
                "職業",
                (CourseOdds("科目1", 0.85, 0.1, 0.05), CourseOdds("科目2", 0.05, 0.05, 0.9)),
                1_000,
            )
        ],
        Layout.SEPARATE: [],
    }
    judgments = Judgments(
        frozenset({"科目1", "科目2"}),
        {("職業", "科目1"): Judgment.EXPECTED, ("職業", "科目2"): Judgment.UNRELATED},
    )

    lines = render(
        calibration_document(stopped="費用の上限 1 円に達した"), trials, measured, judgments
    ).splitlines()

    assert lines[0] == (
        "Jev の校正 jev(2026-10-30T12:00:00+09:00、モデル jev-1.14.0、問いの指紋 abcd1234、"
        "元の結果 selection の 1 回目、1 職業)"
    )
    assert "  途中で止めた: 費用の上限 1 円に達した" in lines
    assert lines[3].startswith("1 職業 1 回(候補 20 科目をまとめる): 1 職業、2 科目")
    assert "  中心: ECE 0.100、Brier 0.013(2 科目)" in lines
    assert "    確率 0.8〜0.9: 1 科目、平均 0.85、当たり 100%" in lines
    assert lines[-3:] == [
        "    選んだ 1 科目のうち関係なし: 選び手 100.0%、Jev 0.0%",
        "    候補にある期待する科目 1 のうち選んだ割合: 選び手 0.0%、Jev 100.0%",
        "    中心 0 科目の適合率: 選び手 -、Jev -",
    ]
    assert not any(line.startswith("1 科目 1 回") for line in lines)


def written(tmp_path: Path, name: str, content: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return path


def grading_files(tmp_path: Path, heldout: bool = False) -> tuple[Path, Path]:
    dataset = written(
        tmp_path,
        "occupations.json",
        {
            "year": 2026,
            "department": "情",
            "heldout": heldout,
            "occupations": [
                {"name": "職業", "skills": ["甲", "乙", "丙"], "expected": {"科目1": "理由"}}
            ],
        },
    )
    judgments = written(
        tmp_path,
        "judgments.json",
        {
            "year": 2026,
            "department": "情",
            "parts": [["科目1"], ["科目2"]],
            "occupations": [
                {
                    "name": "職業",
                    "courses": [
                        {
                            "name": "科目1",
                            "page": "1",
                            "votes": {
                                judge: {"label": "core", "evidence": "根拠"}
                                for judge in ("engineer", "professor")
                            },
                        }
                    ],
                }
            ],
        },
    )
    return dataset, judgments


def source_run(tmp_path: Path, graded_by: tuple[Path, Path], **config: Any) -> Path:
    dataset, judgments = graded_by
    return written(
        tmp_path,
        "run.json",
        {
            "label": "selection",
            "config": {
                "profiles": "analyzed",
                "dataset": digest(dataset.read_bytes()),
                "judgments": digest(judgments.read_bytes()),
                **config,
            },
            "summary": {"yen_per_plan": 0.99},
            "trials": [run_trial()],
        },
    )


def run_main(run: Path, dataset: Path, judgments: Path) -> None:
    main(
        [
            "run",
            str(run),
            "--label",
            "jev",
            "--dataset",
            str(dataset),
            "--judgments",
            str(judgments),
        ]
    )


def test_run_refuses_the_heldout_set(tmp_path: Path) -> None:
    dataset, judgments = grading_files(tmp_path, heldout=True)

    with pytest.raises(SystemExit, match="確かめ用"):
        run_main(source_run(tmp_path, (dataset, judgments)), dataset, judgments)


def test_run_refuses_a_run_that_did_not_read_the_occupation(tmp_path: Path) -> None:
    dataset, judgments = grading_files(tmp_path)

    with pytest.raises(SystemExit, match="読み取りを通って採点した"):
        run_main(
            source_run(tmp_path, (dataset, judgments), profiles="handwritten"), dataset, judgments
        )


def test_run_refuses_judgments_other_than_the_ones_the_run_was_graded_with(tmp_path: Path) -> None:
    dataset, judgments = grading_files(tmp_path)

    with pytest.raises(SystemExit, match="結果と違う"):
        run_main(
            source_run(tmp_path, (dataset, judgments), judgments="00000000"), dataset, judgments
        )


def test_run_says_it_cannot_read_a_run_missing_its_summary(tmp_path: Path) -> None:
    dataset, judgments = grading_files(tmp_path)
    run = source_run(tmp_path, (dataset, judgments))
    content = json.loads(run.read_text(encoding="utf-8"))
    del content["summary"]
    run.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SystemExit, match="実験の結果を読めません: KeyError"):
        run_main(run, dataset, judgments)


def test_run_refuses_a_candidate_the_judges_never_saw(tmp_path: Path) -> None:
    dataset, judgments = grading_files(tmp_path)
    run = source_run(tmp_path, (dataset, judgments))
    content = json.loads(run.read_text(encoding="utf-8"))
    content["trials"][0]["candidates"].append("科目9")
    run.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SystemExit, match="判定していない候補があります: 科目9"):
        run_main(run, dataset, judgments)


def test_run_asks_for_the_jev_key_before_it_calls_anything(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.delenv("JEV_API_KEY", raising=False)
    dataset, judgments = grading_files(tmp_path)

    with pytest.raises(SystemExit, match="JEV_API_KEY"):
        run_main(source_run(tmp_path, (dataset, judgments)), dataset, judgments)


def test_show_reads_a_saved_result_with_its_own_judgments_without_calling_jev(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    saved = written(
        tmp_path,
        "calibration.json",
        calibration_document(
            trials=[run_trial()],
            layouts={
                "grouped": [
                    {
                        "occupation": "職業",
                        "input_tokens": 1_000,
                        "odds": [
                            {
                                "name": "科目1",
                                "core": 0.85,
                                "foundation": 0.1,
                                "unrelated": 0.05,
                                "judgment": "expected",
                            },
                            {
                                "name": "科目2",
                                "core": 0.05,
                                "foundation": 0.05,
                                "unrelated": 0.9,
                                "judgment": "unrelated",
                            },
                        ],
                    }
                ]
            },
        ),
    )

    main(["show", str(saved)])

    output = capsys.readouterr().out
    assert "1 職業 1 回(候補 20 科目をまとめる): 1 職業、2 科目" in output
    assert "選んだ 1 科目のうち関係なし: 選び手 100.0%、Jev 0.0%" in output


def test_a_result_already_written_under_the_same_name_is_not_overwritten(tmp_path: Path) -> None:
    taken = tmp_path / "20261030-120000-jev.json"
    taken.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit, match="結果を書く場所を作れません"):
        reserve(tmp_path, [taken])
    assert taken.read_text(encoding="utf-8") == "{}"
