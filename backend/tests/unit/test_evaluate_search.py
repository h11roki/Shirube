from pathlib import Path

import pytest

from app.application.evaluate_search import (
    CaseResult,
    EvaluateSearch,
    EvaluationCase,
    EvaluationDataset,
    EvaluationError,
    EvaluationReport,
    HandwrittenProfiles,
)
from app.application.judging import expected_courses
from app.application.search_courses import SearchCourses, query_and_skills
from app.domain.chunk import ChunkSection
from app.domain.occupation import OccupationProfile
from app.domain.ranking import ChunkHit
from app.presentation.cli.evaluate import render, render_means
from app.presentation.cli.evaluation_data import (
    DEFAULT_DATASET,
    DEFAULT_JUDGMENTS,
    HELDOUT_DATASET,
    HELDOUT_JUDGMENTS,
    judged_courses,
    load_dataset,
    read_document,
)
from tests.fakes import (
    FakeChunkSearch,
    FakeEmbedder,
    FakeOccupationAnalyzer,
    courses_ranked_by,
)


def search_over(similarities: dict[str, float]) -> SearchCourses:
    return courses_ranked_by(similarities)[1]


def evaluate(search: SearchCourses, *cases: EvaluationCase) -> EvaluationReport:
    dataset = EvaluationDataset(2026, "情", cases)
    return EvaluateSearch(search, HandwrittenProfiles(dataset)).run(dataset)


def test_recall_counts_expected_courses_within_each_cutoff() -> None:
    similarities = {f"科目{rank:02d}": 1.0 - rank / 100 for rank in range(1, 26)}
    case = EvaluationCase("職業", ("甲", "乙", "丙"), ("科目01", "科目10", "科目15", "科目25"))

    report = evaluate(search_over(similarities), case)

    [result] = report.results
    assert result.query == "職業\n甲\n乙\n丙"
    assert result.ranks == (("科目01", 1), ("科目10", 10), ("科目15", 15), ("科目25", None))
    assert result.recall(10) == 0.5
    assert result.recall(20) == 0.75
    assert report.mean_recall(10) == 0.5


def test_a_course_first_for_a_skill_counts_at_the_turn_the_skill_gives_it() -> None:
    similarities = {f"科目{rank:02d}": 1.0 - rank / 100 for rank in range(1, 26)}
    repository, _ = courses_ranked_by(similarities)
    hits = [
        ChunkHit(f"{10000 + index}", ChunkSection.OVERVIEW, similarity)
        for index, similarity in enumerate(similarities.values())
    ]
    chunks = FakeChunkSearch(
        hits, hits_by_length={1.0: [ChunkHit("10024", ChunkSection.OVERVIEW, 0.9)]}
    )
    case = EvaluationCase("職業", ("甲", "乙", "丙"), ("科目25",))

    report = evaluate(SearchCourses(repository, chunks, FakeEmbedder(), query_and_skills), case)

    assert report.results[0].ranks == (("科目25", 2),)


def test_the_queries_of_every_case_are_embedded_in_one_call() -> None:
    embedder = FakeEmbedder()
    cases = (
        EvaluationCase("職業A", ("甲", "乙", "丙"), ("科目01",)),
        EvaluationCase("職業B", ("丁", "戊", "己"), ("科目01",)),
    )

    evaluate(courses_ranked_by({"科目01": 0.9}, embedder)[1], *cases)

    assert embedder.calls == [
        ["職業A\n甲\n乙\n丙", "甲", "乙", "丙", "職業B\n丁\n戊\n己", "丁", "戊", "己"]
    ]


def test_expected_course_names_outside_the_candidates_are_an_error() -> None:
    case = EvaluationCase("職業", ("甲", "乙", "丙"), ("科目01", "存在しない科目"))

    with pytest.raises(EvaluationError, match="存在しない科目"):
        evaluate(search_over({"科目01": 0.9}), case)


def test_llm_profiles_search_with_the_interpretation_like_recommending() -> None:
    profile = OccupationProfile("職業", "広い職業", "広く読んだ", ("甲", "乙", "丙"))
    analyzer = FakeOccupationAnalyzer({"職業": profile})
    dataset = EvaluationDataset(
        2026, "情", (EvaluationCase("職業", ("甲", "乙", "丙"), ("科目01",)),)
    )

    report = EvaluateSearch(search_over({"科目01": 0.9}), analyzer).run(dataset)

    assert analyzer.calls == ["職業"]
    assert report.results[0].query == profile.query == "広い職業\n甲\n乙\n丙"


def test_occupations_are_read_only_after_the_course_names_are_checked() -> None:
    analyzer = FakeOccupationAnalyzer({})
    dataset = EvaluationDataset(
        2026, "情", (EvaluationCase("職業", ("甲", "乙", "丙"), ("存在しない科目",)),)
    )

    with pytest.raises(EvaluationError, match="存在しない科目"):
        EvaluateSearch(search_over({"科目01": 0.9}), analyzer).run(dataset)

    assert analyzer.calls == []


@pytest.mark.parametrize(
    ("occupation", "skills", "expected", "message"),
    [
        ("  ", ("スキル",), ("甲",), "職業名が空です"),
        ("職業", (), ("甲",), "職業: スキルが空です"),
        ("職業", ("",), ("甲",), "職業: スキルが空です"),
        ("組込み\nエンジニア", ("スキル",), ("甲",), "職業名に改行があります"),
        ("職業", ("C 言語\nマイコン",), ("甲",), "職業: スキルに改行があります"),
        ("職業", ("C 言語\rマイコン",), ("甲",), "職業: スキルに改行があります"),
        ("職業", ("C 言語", " C 言語"), ("甲",), "職業: スキルが重複しています"),
        ("職業", ("甲", "乙"), ("甲",), "職業: スキルは 3〜6 個にしてください"),
        ("職業", tuple("甲乙丙丁戊己庚"), ("甲",), "職業: スキルは 3〜6 個にしてください"),
        ("職業", ("甲", "乙", "丙"), (), "職業: 期待する科目がありません"),
    ],
    ids=[
        "blank-occupation",
        "no-skills",
        "blank-skill",
        "multiline-occupation",
        "multiline-skill",
        "carriage-return-in-skill",
        "duplicated-skill",
        "too-few-skills",
        "too-many-skills",
        "no-expected-courses",
    ],
)
def test_case_without_a_name_usable_skills_or_expected_courses_is_rejected(
    occupation: str, skills: tuple[str, ...], expected: tuple[str, ...], message: str
) -> None:
    with pytest.raises(EvaluationError, match=message):
        EvaluationCase(occupation, skills, expected)


def test_dataset_without_cases_or_with_repeated_occupations_is_rejected() -> None:
    case = EvaluationCase("職業", ("甲", "乙", "丙"), ("甲",))

    with pytest.raises(EvaluationError, match="評価する職業がありません"):
        EvaluationDataset(2026, "情", ())
    with pytest.raises(EvaluationError, match="同じ職業が 2 回あります: 職業"):
        EvaluationDataset(2026, "情", (case, case))


def test_handwritten_profiles_read_the_occupation_as_written() -> None:
    case = EvaluationCase("組込みエンジニア", ("C 言語", "マイコン", "電子回路"), ("甲",))

    profile = HandwrittenProfiles(EvaluationDataset(2026, "情", (case,))).analyze(
        "組込みエンジニア"
    )

    assert profile == OccupationProfile(
        "組込みエンジニア", "組込みエンジニア", None, ("C 言語", "マイコン", "電子回路")
    )
    assert profile.query == "組込みエンジニア\nC 言語\nマイコン\n電子回路"


def test_report_lists_the_query_recalls_and_ranks() -> None:
    report = EvaluationReport((CaseResult("職業", "職業\nスキル", (("甲", 3), ("乙", None))),))

    assert render(report) == (
        "職業  @10 0.50  @20 0.50\n"
        "  検索文: 職業 / スキル\n"
        "  甲 3 位 / 乙 圏外\n"
        "平均  @10 0.50  @20 0.50"
    )


def test_means_leave_out_every_occupation() -> None:
    report = EvaluationReport((CaseResult("職業", "職業\nスキル", (("甲", 3), ("乙", None))),))

    assert render_means(report) == "平均  @10 0.50  @20 0.50"


COMMITTED_FILES = [(DEFAULT_DATASET, DEFAULT_JUDGMENTS), (HELDOUT_DATASET, HELDOUT_JUDGMENTS)]
COMMITTED_NAMES = ["development", "heldout"]
COMMITTED = pytest.mark.parametrize(
    ("dataset_path", "judgments_path"), COMMITTED_FILES, ids=COMMITTED_NAMES
)


def test_committed_dataset_is_the_default_and_has_fifty_occupations() -> None:
    dataset = load_dataset(DEFAULT_DATASET)

    assert (dataset.year, dataset.department) == (2026, "情")
    assert len(dataset.cases) == 50


def test_heldout_has_twenty_other_occupations_judged_like_the_development_set() -> None:
    dataset, heldout = load_dataset(DEFAULT_DATASET), load_dataset(HELDOUT_DATASET)

    assert (heldout.year, heldout.department) == (dataset.year, dataset.department)
    assert (heldout.heldout, dataset.heldout) == (True, False)
    assert len(heldout.cases) == 20
    assert not {case.occupation for case in heldout.cases} & {
        case.occupation for case in dataset.cases
    }
    development, heldout_judgments = (
        read_document(DEFAULT_JUDGMENTS),
        read_document(HELDOUT_JUDGMENTS),
    )
    for key in ("year", "department", "model", "judges", "parts"):
        assert heldout_judgments[key] == development[key], key


@pytest.mark.parametrize(
    "judgments_path", [judgments for _, judgments in COMMITTED_FILES], ids=COMMITTED_NAMES
)
def test_judgments_cover_188_courses_with_every_judge_on_both_halves(judgments_path: Path) -> None:
    judgments = read_document(judgments_path)
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


@COMMITTED
def test_expected_courses_follow_the_judges_majority_and_the_decisions(
    dataset_path: Path, judgments_path: Path
) -> None:
    judgments, dataset = read_document(judgments_path), read_document(dataset_path)
    judged = {
        occupation["name"]: judged_courses(occupation) for occupation in judgments["occupations"]
    }
    for occupation, courses in judged.items():
        for course in courses:
            assert (course.decision is not None) == (len(course.cores) == 1), (
                occupation,
                course.name,
            )

    assert (dataset["year"], dataset["department"]) == (judgments["year"], judgments["department"])
    assert {
        occupation["name"]: list(occupation["expected"].items())
        for occupation in dataset["occupations"]
    } == {
        occupation: list(expected_courses(courses).items())
        for occupation, courses in judged.items()
    }


VALID = '{"name": "職業", "skills": ["C", "D", "E"], "expected": {"甲": "理由"}}'


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


def test_heldout_must_be_true_or_false(tmp_path: Path) -> None:
    path = tmp_path / "occupations.json"
    path.write_text(
        '{"year": 2026, "department": "情", "heldout": "yes", "occupations": []}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="heldout は true か false"):
        load_dataset(path)


@pytest.mark.parametrize("year", ["true", "2026.5", '"2026"'])
def test_year_must_be_an_integer(tmp_path: Path, year: str) -> None:
    path = tmp_path / "occupations.json"
    path.write_text(
        f'{{"year": {year}, "department": "情", "occupations": [{VALID}]}}', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="year は整数"):
        load_dataset(path)
