from pathlib import Path

import pytest

from app.application.evaluate_search import EvaluationCase, EvaluationDataset, EvaluationError
from app.application.evaluate_selection import (
    EvaluateSelection,
    Judgement,
    SelectionReport,
    SelectionResult,
    judgement_of,
)
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CourseChoice, Relevance
from app.presentation.cli.evaluate_selection import load_judgements, render
from tests.fakes import FakeCourseSelector, courses_ranked_by

DATASET = EvaluationDataset(
    2026, "情", (EvaluationCase("職業", ("甲", "乙", "丙"), ("科目A", "科目D")),)
)
SIMILARITIES = {"科目A": 0.9, "科目B": 0.8, "科目C": 0.7, "科目D": 0.6}
JUDGEMENTS = {
    ("職業", "科目A"): Judgement.EXPECTED,
    ("職業", "科目B"): Judgement.FOUNDATION,
    ("職業", "科目D"): Judgement.EXPECTED,
}


@pytest.mark.parametrize(
    ("labels", "decision", "judgement"),
    [
        (["core", "core", "foundation"], None, Judgement.EXPECTED),
        (["core", "foundation", "foundation"], "core", Judgement.EXPECTED),
        (["core", "foundation", "foundation"], "foundation", Judgement.FOUNDATION),
        (["foundation", "foundation"], None, Judgement.FOUNDATION),
        (["foundation"], None, Judgement.MINORITY),
        ([], None, Judgement.UNRELATED),
    ],
    ids=["two-core", "decided-core", "decided-foundation", "two-foundation", "one-vote", "none"],
)
def test_judgement_follows_the_majority_and_the_decision(
    labels: list[str], decision: str | None, judgement: Judgement
) -> None:
    assert judgement_of(labels, decision) is judgement


def test_selection_is_compared_with_the_judgements_using_the_handwritten_skills() -> None:
    repository, search = courses_ranked_by(SIMILARITIES)
    selector = FakeCourseSelector(
        [
            CourseChoice("科目C", Relevance.FOUNDATION, "理由C"),
            CourseChoice("科目A", Relevance.CORE, "理由A"),
            CourseChoice("科目B", Relevance.FOUNDATION, "理由B"),
        ]
    )

    report = EvaluateSelection(search, repository, selector, 3).run(DATASET, JUDGEMENTS)

    [(profile, candidates)] = selector.calls
    assert profile == OccupationProfile("職業", "職業", None, ("甲", "乙", "丙"))
    assert [candidate.name for candidate in candidates] == ["科目A", "科目B", "科目C"]
    assert report == SelectionReport(
        (
            SelectionResult(
                "職業",
                (
                    ("科目A", Relevance.CORE, Judgement.EXPECTED),
                    ("科目B", Relevance.FOUNDATION, Judgement.FOUNDATION),
                    ("科目C", Relevance.FOUNDATION, Judgement.UNRELATED),
                ),
                (("科目A", Relevance.CORE), ("科目D", None)),
                ("科目D",),
            ),
        )
    )


def test_expected_courses_that_disagree_with_the_judgements_stop_the_evaluation() -> None:
    repository, search = courses_ranked_by(SIMILARITIES)
    judgements = {("職業", "科目A"): Judgement.EXPECTED}

    with pytest.raises(EvaluationError, match="職業: 期待する科目が判定と合いません"):
        EvaluateSelection(search, repository, FakeCourseSelector([]), 3).run(DATASET, judgements)


def test_judgements_are_loaded_from_the_votes_and_decisions(tmp_path: Path) -> None:
    path = tmp_path / "judgments.json"
    path.write_text(
        '{"occupations": [{"name": "職業", "courses": ['
        '{"name": "科目A", "votes": {"a": {"label": "core"}, "b": {"label": "core"}}},'
        '{"name": "科目B", "votes": {"a": {"label": "core"}, "b": {"label": "foundation"}},'
        ' "decision": "foundation"}'
        "]}]}",
        encoding="utf-8",
    )

    assert load_judgements(path) == {
        ("職業", "科目A"): Judgement.EXPECTED,
        ("職業", "科目B"): Judgement.FOUNDATION,
    }


def test_render_counts_picks_by_judgement_and_names_the_misses() -> None:
    report = SelectionReport(
        (
            SelectionResult(
                "職業",
                (
                    ("科目A", Relevance.CORE, Judgement.EXPECTED),
                    ("科目B", Relevance.FOUNDATION, Judgement.FOUNDATION),
                    ("科目C", Relevance.FOUNDATION, Judgement.UNRELATED),
                ),
                (("科目A", Relevance.CORE), ("科目E", None), ("科目D", None)),
                ("科目D",),
            ),
        )
    )

    summary = (
        "  中心 1 科目: 期待 1 / 土台 0 / 少数 0 / 関係なし 0\n"
        "  土台 2 科目: 期待 0 / 土台 1 / 少数 0 / 関係なし 1\n"
        "  期待する科目 3: 中心 1 / 土台 0 / 選ばず 1 / 検索の上位に無い 1\n"
    )
    assert render(report) == (
        "職業\n" + summary + "  関係なしを選んだ: 科目C\n"
        "  選ばなかった期待する科目: 科目E、科目D\n"
        "合計\n"
        + summary
        + "  中心の適合率 100%、期待する科目を中心に選んだ割合 33%、選んだ科目のうち関係なし 33%"
    )
