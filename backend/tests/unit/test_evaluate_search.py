from dataclasses import replace
from pathlib import Path

import pytest

from app.application.evaluate_search import (
    CaseResult,
    EvaluateSearch,
    EvaluationCase,
    EvaluationDataset,
    EvaluationError,
    EvaluationReport,
)
from app.application.search_courses import SearchCourses
from app.domain.chunk import ChunkSection
from app.domain.ranking import ChunkHit
from app.presentation.cli.evaluate import DEFAULT_DATASET, load_dataset, render
from tests.builders import course_section, syllabus
from tests.fakes import FakeChunkSearch, FakeCourseRepository, FakeEmbedder


def search_over(similarities: dict[str, float]) -> SearchCourses:
    codes = [f"{10000 + number}" for number in range(len(similarities))]
    names = list(similarities)
    repository = FakeCourseRepository(
        sections=tuple(
            replace(course_section(code), name=name)
            for code, name in zip(codes, names, strict=True)
        ),
        syllabi=tuple(syllabus(code) for code in codes),
    )
    hits = [
        ChunkHit(code, ChunkSection.OVERVIEW, similarities[name])
        for code, name in zip(codes, names, strict=True)
    ]
    return SearchCourses(repository, FakeChunkSearch(hits), FakeEmbedder())


def test_recall_counts_expected_courses_within_each_cutoff() -> None:
    similarities = {f"科目{rank:02d}": 1.0 - rank / 100 for rank in range(1, 26)}
    case = EvaluationCase("職業", ("スキル",), ("科目01", "科目10", "科目15", "科目25"))

    report = EvaluateSearch(search_over(similarities)).run(EvaluationDataset(2026, "情", (case,)))

    [result] = report.results
    assert result.ranks == (("科目01", 1), ("科目10", 10), ("科目15", 15), ("科目25", None))
    assert result.recall(10) == 0.5
    assert result.recall(20) == 0.75
    assert report.mean_recall(10) == 0.5


def test_expected_course_names_outside_the_candidates_are_an_error() -> None:
    case = EvaluationCase("職業", ("スキル",), ("科目01", "存在しない科目"))

    with pytest.raises(EvaluationError, match="存在しない科目"):
        EvaluateSearch(search_over({"科目01": 0.9})).run(EvaluationDataset(2026, "情", (case,)))


@pytest.mark.parametrize(
    ("occupation", "skills", "expected", "message"),
    [
        ("  ", ("スキル",), ("甲",), "職業名が空です"),
        ("職業", (), ("甲",), "職業: スキルが空です"),
        ("職業", ("",), ("甲",), "職業: スキルが空です"),
        ("職業", ("スキル",), (), "職業: 期待する科目がありません"),
    ],
    ids=["blank-occupation", "no-skills", "blank-skill", "no-expected-courses"],
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


def test_report_lists_recalls_and_ranks() -> None:
    report = EvaluationReport((CaseResult("職業", (("甲", 3), ("乙", None))),))

    assert (
        render(report) == "職業  @10 0.50  @20 0.50\n  甲 3 位 / 乙 圏外\n平均  @10 0.50  @20 0.50"
    )


def test_committed_dataset_is_the_default_and_has_ten_occupations() -> None:
    dataset = load_dataset(DEFAULT_DATASET)

    assert (dataset.year, dataset.department) == (2026, "情")
    assert len(dataset.cases) == 10
    assert all(len(case.skills) >= 3 and len(case.expected) >= 5 for case in dataset.cases)


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
