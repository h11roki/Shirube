import json
from pathlib import Path
from typing import Any

import pytest

from app.application.evaluate_search import (
    CaseResult,
    EvaluateSearch,
    EvaluationCase,
    EvaluationDataset,
    EvaluationError,
    EvaluationReport,
    with_analyzed_skills,
)
from app.application.search_courses import SearchCourses
from app.domain.occupation import OccupationProfile
from app.presentation.cli.evaluate import DEFAULT_DATASET, _unique_keys, load_dataset, render
from tests.fakes import (
    FakeOccupationAnalyzer,
    courses_ranked_by,
)


def search_over(similarities: dict[str, float]) -> SearchCourses:
    return courses_ranked_by(similarities)[1]


def test_recall_counts_expected_courses_within_each_cutoff() -> None:
    similarities = {f"科目{rank:02d}": 1.0 - rank / 100 for rank in range(1, 26)}
    case = EvaluationCase("職業", ("スキル",), ("科目01", "科目10", "科目15", "科目25"))

    report = EvaluateSearch(search_over(similarities)).run(EvaluationDataset(2026, "情", (case,)))

    [result] = report.results
    assert result.query == case.query
    assert result.ranks == (("科目01", 1), ("科目10", 10), ("科目15", 15), ("科目25", None))
    assert result.recall(10) == 0.5
    assert result.recall(20) == 0.75
    assert report.mean_recall(10) == 0.5


def test_expected_course_names_outside_the_candidates_are_an_error() -> None:
    case = EvaluationCase("職業", ("スキル",), ("科目01", "存在しない科目"))

    with pytest.raises(EvaluationError, match="存在しない科目"):
        EvaluateSearch(search_over({"科目01": 0.9})).run(EvaluationDataset(2026, "情", (case,)))


def test_analyzed_skills_replace_only_the_handwritten_skills() -> None:
    profile = OccupationProfile("職業", "別の名前の職業", None, ("甲", "乙", "丙"))
    analyzer = FakeOccupationAnalyzer({"職業": profile})
    dataset = EvaluationDataset(
        2026, "情", (EvaluationCase("職業", ("手書きのスキル",), ("科目01",)),)
    )

    analyzed = with_analyzed_skills(dataset, analyzer)

    assert analyzer.calls == ["職業"]
    assert analyzed == EvaluationDataset(
        2026, "情", (EvaluationCase("職業", ("甲", "乙", "丙"), ("科目01",)),)
    )
    assert analyzed.cases[0].query == "職業\n甲\n乙\n丙"


@pytest.mark.parametrize(
    ("occupation", "skills", "expected", "message"),
    [
        ("  ", ("スキル",), ("甲",), "職業名が空です"),
        ("職業", (), ("甲",), "職業: スキルが空です"),
        ("職業", ("",), ("甲",), "職業: スキルが空です"),
        ("組込み\nエンジニア", ("スキル",), ("甲",), "職業名に改行があります"),
        ("職業", ("C 言語\nマイコン",), ("甲",), "職業: スキルに改行があります"),
        ("職業", ("C 言語\rマイコン",), ("甲",), "職業: スキルに改行があります"),
        ("職業", ("スキル",), (), "職業: 期待する科目がありません"),
    ],
    ids=[
        "blank-occupation",
        "no-skills",
        "blank-skill",
        "multiline-occupation",
        "multiline-skill",
        "carriage-return-in-skill",
        "no-expected-courses",
    ],
)
def test_case_without_a_name_skills_or_expected_courses_is_rejected(
    occupation: str, skills: tuple[str, ...], expected: tuple[str, ...], message: str
) -> None:
    with pytest.raises(EvaluationError, match=message):
        EvaluationCase(occupation, skills, expected)


def test_dataset_without_cases_or_with_repeated_occupations_is_rejected() -> None:
    case = EvaluationCase("職業", ("スキル",), ("甲",))

    with pytest.raises(EvaluationError, match="評価する職業がありません"):
        EvaluationDataset(2026, "情", ())
    with pytest.raises(EvaluationError, match="同じ職業が 2 回あります: 職業"):
        EvaluationDataset(2026, "情", (case, case))


def test_query_joins_the_occupation_and_its_skills() -> None:
    case = EvaluationCase("組込みエンジニア", ("C 言語", "マイコン"), ("甲",))

    assert case.query == "組込みエンジニア\nC 言語\nマイコン"


def test_report_lists_the_query_recalls_and_ranks() -> None:
    report = EvaluationReport((CaseResult("職業", "職業\nスキル", (("甲", 3), ("乙", None))),))

    assert render(report) == (
        "職業  @10 0.50  @20 0.50\n"
        "  検索文: 職業 / スキル\n"
        "  甲 3 位 / 乙 圏外\n"
        "平均  @10 0.50  @20 0.50"
    )


def test_committed_dataset_is_the_default_and_has_ten_occupations() -> None:
    dataset = load_dataset(DEFAULT_DATASET)

    assert (dataset.year, dataset.department) == (2026, "情")
    assert len(dataset.cases) == 10
    assert all(len(case.skills) >= 3 for case in dataset.cases)


JUDGMENTS = DEFAULT_DATASET.with_name("judgments.json")
LABELS = {"core", "foundation"}
REASON_ORDER = ("professor", "student", "engineer")


def strict_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)


def test_judgments_cover_188_courses_with_every_judge_on_both_halves() -> None:
    judgments = strict_json(JUDGMENTS)
    first, second = judgments["parts"]
    halves = set(first) | set(second)
    voted: dict[str, set[str]] = {judge: set() for judge in judgments["judges"]}
    pages: dict[str, str] = {}
    for occupation in judgments["occupations"]:
        names = [course["name"] for course in occupation["courses"]]
        assert len(names) == len(set(names)), occupation["name"]
        for course in occupation["courses"]:
            where = (occupation["name"], course["name"])
            assert pages.setdefault(course["name"], course["page"]) == course["page"], where
            assert course["votes"].keys() <= voted.keys(), where
            for judge, vote in course["votes"].items():
                assert 0 < len(vote["evidence"]) <= 40, (*where, judge)
                voted[judge].add(course["name"])

    assert len(first) + len(second) == len(halves) == 188
    for judge, courses in voted.items():
        assert courses <= halves, judge
        assert courses & set(first) and courses & set(second), judge


def test_expected_courses_follow_the_judges_majority_and_the_documented_aggregation() -> None:
    judgments = strict_json(JUDGMENTS)
    majority: dict[str, list[tuple[str, str]]] = {}
    for occupation in judgments["occupations"]:
        ranked: list[tuple[int, str, str]] = []
        for course in occupation["courses"]:
            where = (occupation["name"], course["name"])
            votes = course["votes"]
            assert all(vote["label"] in LABELS for vote in votes.values()), where
            cores = [judge for judge in REASON_ORDER if votes.get(judge, {}).get("label") == "core"]
            if len(cores) == 1:
                assert course.get("decision") in LABELS, where
            else:
                assert "decision" not in course, where
            if len(cores) >= 2 or course.get("decision") == "core":
                ranked.append((-len(cores), course["name"], votes[cores[0]]["evidence"]))
        majority[occupation["name"]] = [(name, why) for _, name, why in sorted(ranked)]

    dataset = strict_json(DEFAULT_DATASET)

    assert (dataset["year"], dataset["department"]) == (judgments["year"], judgments["department"])
    assert {
        occupation["name"]: list(occupation["expected"].items())
        for occupation in dataset["occupations"]
    } == majority


VALID = '{"name": "職業", "skills": ["C"], "expected": {"甲": "理由"}}'


@pytest.mark.parametrize(
    ("occupations", "message"),
    [
        ('{"name": null, "skills": ["C"], "expected": {"甲": "理由"}}', "name は文字列"),
        (
            '{"name": "職業", "skills": "C 言語", "expected": {"甲": "理由"}}',
            "skills は文字列の配列",
        ),
        ('{"name": "職業", "skills": [], "expected": {"甲": "理由"}}', "スキルが空です"),
        ('{"name": "職業", "skills": ["C"], "expected": ["甲"]}', "expected は科目名から理由"),
        ('{"name": "職業", "skills": ["C"], "expected": {"甲": ""}}', "expected は科目名から理由"),
        (
            '{"name": "職業", "skills": ["C"], "expected": {"甲": "理由", "甲": "別の理由"}}',
            "同じ項目が 2 回あります: 甲",
        ),
        (f"{VALID}, {VALID}", "同じ職業が 2 回あります: 職業"),
    ],
    ids=[
        "name-not-a-string",
        "skills-as-a-string",
        "no-skills",
        "expected-as-a-list",
        "empty-reason",
        "duplicated-course",
        "duplicated-occupation",
    ],
)
def test_malformed_dataset_is_rejected(tmp_path: Path, occupations: str, message: str) -> None:
    path = tmp_path / "occupations.json"
    path.write_text(
        f'{{"year": 2026, "department": "情", "occupations": [{occupations}]}}', encoding="utf-8"
    )

    with pytest.raises(ValueError, match=message):
        load_dataset(path)


@pytest.mark.parametrize("year", ["true", "2026.5", '"2026"'])
def test_year_must_be_an_integer(tmp_path: Path, year: str) -> None:
    path = tmp_path / "occupations.json"
    path.write_text(
        f'{{"year": {year}, "department": "情", "occupations": [{VALID}]}}', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="year は整数"):
        load_dataset(path)
