import json
import sys
from pathlib import Path

import pytest

from app.application.evaluate_search import EvaluationCase, EvaluationDataset, EvaluationError
from app.application.evaluate_selection import (
    EvaluateSelection,
    ExpectedCourse,
    Judgment,
    Judgments,
    Pick,
    SelectionReport,
    SelectionResult,
    UnlinkedPick,
    judgment_of,
)
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CourseChoice, Relevance
from app.presentation.cli import evaluate_selection as evaluate_selection_cli
from app.presentation.cli.evaluate_selection import render
from app.presentation.cli.evaluation_data import load_judgments
from tests.fakes import FakeCourseSelector, courses_ranked_by

DATASET = EvaluationDataset(
    2026, "情", (EvaluationCase("職業", ("甲", "乙", "丙"), ("科目A", "科目D")),)
)
SIMILARITIES = {"科目A": 0.9, "科目B": 0.8, "科目C": 0.7, "科目D": 0.6}
JUDGMENTS = Judgments(
    frozenset(SIMILARITIES),
    {
        ("職業", "科目A"): Judgment.EXPECTED,
        ("職業", "科目B"): Judgment.FOUNDATION,
        ("職業", "科目D"): Judgment.EXPECTED,
    },
)
CORE, FOUNDATION = Relevance.CORE, Relevance.FOUNDATION


@pytest.mark.parametrize(
    ("votes", "decision", "judgment"),
    [
        ([CORE, CORE, FOUNDATION], None, Judgment.EXPECTED),
        ([CORE, FOUNDATION, FOUNDATION], CORE, Judgment.EXPECTED),
        ([CORE, FOUNDATION, FOUNDATION], FOUNDATION, Judgment.FOUNDATION),
        ([CORE], FOUNDATION, Judgment.FOUNDATION),
        ([FOUNDATION, FOUNDATION], None, Judgment.FOUNDATION),
        ([FOUNDATION], None, Judgment.MINORITY),
        ([], None, Judgment.UNRELATED),
    ],
    ids=[
        "two-core",
        "decided-core",
        "decided-foundation",
        "lone-core-decided-foundation",
        "two-foundation",
        "one-vote",
        "none",
    ],
)
def test_judgment_follows_the_majority_and_the_decision(
    votes: list[Relevance], decision: Relevance | None, judgment: Judgment
) -> None:
    assert judgment_of(votes, decision) is judgment


def test_selection_is_compared_with_the_judgments_using_the_handwritten_skills() -> None:
    repository, search = courses_ranked_by(SIMILARITIES)
    selector = FakeCourseSelector(
        [
            CourseChoice("科目C", Relevance.FOUNDATION, "理由C", "科目A"),
            CourseChoice("科目A", Relevance.CORE, "理由A"),
            CourseChoice("科目B", Relevance.FOUNDATION, "理由B", "科目C"),
        ]
    )

    report = EvaluateSelection(search, repository, selector, 3).run(DATASET, JUDGMENTS)

    [(profile, candidates)] = selector.calls
    assert profile == OccupationProfile("職業", "職業", None, ("甲", "乙", "丙"))
    assert [candidate.name for candidate in candidates] == ["科目A", "科目B", "科目C"]
    assert report == SelectionReport(
        (
            SelectionResult(
                "職業",
                (
                    Pick("科目A", Relevance.CORE, Judgment.EXPECTED),
                    Pick("科目C", Relevance.FOUNDATION, Judgment.UNRELATED),
                ),
                (
                    ExpectedCourse("科目A", Relevance.CORE, searched=True, unlinked=False),
                    ExpectedCourse("科目D", None, searched=False, unlinked=False),
                ),
                (UnlinkedPick("科目B", "科目C", Judgment.FOUNDATION),),
            ),
        )
    )


def test_an_expected_course_dropped_as_unlinked_is_not_counted_as_skipped() -> None:
    repository, search = courses_ranked_by(SIMILARITIES)
    selector = FakeCourseSelector(
        [
            CourseChoice("科目B", Relevance.CORE, "理由B"),
            CourseChoice("科目A", Relevance.FOUNDATION, "理由A", "科目C"),
            CourseChoice("科目C", Relevance.FOUNDATION, "理由C", "科目B"),
        ]
    )

    [result] = EvaluateSelection(search, repository, selector, 3).run(DATASET, JUDGMENTS).results

    assert result.expected[0] == ExpectedCourse("科目A", None, searched=True, unlinked=True)
    assert result.unlinked == (UnlinkedPick("科目A", "科目C", Judgment.EXPECTED),)
    assert (result.expected_unlinked, result.skipped) == (("科目A",), ())


def test_expected_courses_that_disagree_with_the_judgments_stop_the_evaluation() -> None:
    repository, search = courses_ranked_by(SIMILARITIES)
    judgments = Judgments(frozenset(SIMILARITIES), {("職業", "科目A"): Judgment.EXPECTED})

    selector = FakeCourseSelector([])

    with pytest.raises(EvaluationError, match="期待する科目が判定と合いません: 職業"):
        EvaluateSelection(search, repository, selector, 3).run(DATASET, judgments)
    assert selector.calls == []


def test_a_candidate_the_judges_did_not_read_stops_before_calling_the_llm() -> None:
    repository, search = courses_ranked_by(SIMILARITIES)
    selector = FakeCourseSelector([])
    judgments = Judgments(frozenset({"科目A", "科目B", "科目D"}), JUDGMENTS.by_course)

    with pytest.raises(EvaluationError, match="判定していない候補があります: 科目C"):
        EvaluateSelection(search, repository, selector, 3).run(DATASET, judgments)
    assert selector.calls == []


def test_expected_course_names_outside_the_candidates_stop_before_calling_the_llm() -> None:
    repository, search = courses_ranked_by(SIMILARITIES)
    selector = FakeCourseSelector([])
    dataset = EvaluationDataset(
        2026, "情", (EvaluationCase("職業", ("甲", "乙", "丙"), ("科目A", "打ち間違い")),)
    )

    with pytest.raises(EvaluationError, match="候補に無い科目名があります: 打ち間違い"):
        EvaluateSelection(search, repository, selector, 3).run(dataset, JUDGMENTS)
    assert selector.calls == []


def write_judgments(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "judgments.json"
    path.write_text(body, encoding="utf-8")
    return path


def judged(name: str, decision: str | None = None, **labels: str) -> dict[str, object]:
    course: dict[str, object] = {
        "name": name,
        "page": "10000",
        "votes": {judge: {"label": label, "evidence": "根拠"} for judge, label in labels.items()},
    }
    if decision is not None:
        course["decision"] = decision
    return course


def judgments_of(*courses: dict[str, object], year: int = 2026) -> str:
    return json.dumps(
        {
            "year": year,
            "department": "情",
            "parts": [["科目A"], ["科目B"]],
            "occupations": [{"name": "職業", "courses": list(courses)}],
        },
        ensure_ascii=False,
    )


def test_judgments_are_loaded_from_the_votes_and_decisions(tmp_path: Path) -> None:
    path = write_judgments(
        tmp_path,
        judgments_of(
            judged("科目A", engineer="core", professor="core"),
            judged("科目B", "foundation", engineer="core", professor="foundation"),
        ),
    )

    assert load_judgments(path, DATASET) == Judgments(
        frozenset({"科目A", "科目B"}),
        {
            ("職業", "科目A"): Judgment.EXPECTED,
            ("職業", "科目B"): Judgment.FOUNDATION,
        },
    )


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (judgments_of(year=2025), "年度と学科が評価データと違います"),
        (judgments_of(judged("科目A"), judged("科目A")), "同じ科目の判定が 2 回あります"),
        (judgments_of(judged("科目A", engineer="unrelated")), "is not a valid Relevance"),
        (judgments_of(judged("科目A", "Core", engineer="core")), "is not a valid Relevance"),
        (
            judgments_of(judged("科目A", "foundation", engineer="core", professor="core")),
            "決定は中心が 1 票だけの科目にだけ付けます",
        ),
        (
            judgments_of(judged("科目A", engineer="core", professor="foundation")),
            "中心が 1 票だけの科目に決定がありません",
        ),
        (judgments_of(judged("科目A", teacher="core")), "知らない判定者の票があります: teacher"),
    ],
    ids=[
        "other-year",
        "same-course-twice",
        "unknown-label",
        "unknown-decision",
        "decision-without-a-split",
        "split-without-a-decision",
        "unknown-judge",
    ],
)
def test_judgments_for_another_year_or_with_wrong_entries_are_rejected(
    tmp_path: Path, body: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        load_judgments(write_judgments(tmp_path, body), DATASET)


def test_render_counts_picks_by_judgment_and_names_the_misses() -> None:
    report = SelectionReport(
        (
            SelectionResult(
                "職業",
                (
                    Pick("科目A", Relevance.CORE, Judgment.EXPECTED),
                    Pick("科目B", Relevance.FOUNDATION, Judgment.FOUNDATION),
                    Pick("科目C", Relevance.FOUNDATION, Judgment.UNRELATED),
                ),
                (
                    ExpectedCourse("科目A", Relevance.CORE, searched=True, unlinked=False),
                    ExpectedCourse("科目E", None, searched=True, unlinked=False),
                    ExpectedCourse("科目G", None, searched=True, unlinked=True),
                    ExpectedCourse("科目D", None, searched=False, unlinked=False),
                ),
                (
                    UnlinkedPick("科目F", "科目B", Judgment.UNRELATED),
                    UnlinkedPick("科目G", "科目C", Judgment.EXPECTED),
                ),
            ),
        )
    )

    summary = (
        "  中心 1 科目、判定は 期待 1 / 土台 0 / 少数 0 / 関係なし 0\n"
        "  土台 2 科目、判定は 期待 0 / 土台 1 / 少数 0 / 関係なし 1\n"
        "  中心につながらず外した土台 2 科目、判定は 期待 1 / 土台 0 / 少数 0 / 関係なし 1\n"
        "  期待する科目 4: 中心 1 / 土台 0 / 外した 1 / 選ばず 1 / 検索の候補に無い 1\n"
    )
    assert render(report) == (
        "職業\n" + summary + "  関係なしを選んだ: 科目C\n"
        "  中心につながらず外した土台: 科目F(→ 科目B)、科目G(→ 科目C)\n"
        "  外した期待する科目: 科目G\n"
        "  選ばなかった期待する科目: 科目E\n"
        "  検索の候補に無かった期待する科目: 科目D\n"
        "合計\n"
        + summary
        + "  中心の適合率 100%、期待する科目を中心に選んだ割合 25%、選んだ科目のうち関係なし 33%"
    )


def test_the_selection_evaluation_refuses_the_heldout_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "occupations.json"
    path.write_text(
        '{"year": 2026, "department": "情", "heldout": true, "occupations": ['
        '{"name": "確かめ用の職業", "skills": ["甲", "乙", "丙"],'
        ' "expected": {"科目01": "理由"}}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["evaluate_selection", str(path)])

    with pytest.raises(SystemExit, match="確かめ用は"):
        evaluate_selection_cli.main()
