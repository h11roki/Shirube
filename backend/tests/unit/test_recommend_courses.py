from collections.abc import Set
from dataclasses import replace

import pytest

from app.application.recommend_courses import RecommendCourses, RecommendStep
from app.application.search_courses import SearchCourses, SearchError, query_and_skills
from app.domain.chunk import ChunkSection
from app.domain.occupation import OccupationProfile
from app.domain.ranking import ChunkHit
from app.domain.recommendation import (
    CourseChoice,
    Recommendation,
    RecommendationError,
    RecommendedCourse,
    Relevance,
)
from app.domain.roadmap import ALL_SEMESTERS
from app.domain.syllabus import Syllabus
from tests.builders import course_section, syllabus
from tests.fakes import (
    FakeChunkSearch,
    FakeCourseRepository,
    FakeCourseSelector,
    FakeEmbedder,
    FakeOccupationAnalyzer,
    courses_ranked_by,
)

PROFILE = OccupationProfile("職業", "解釈した職業", None, ("甲", "乙", "丙"))


def recommend_over(
    similarities: dict[str, float],
    selector: FakeCourseSelector,
    analyzer: FakeOccupationAnalyzer | None = None,
    limit: int = 30,
) -> RecommendCourses:
    repository, search = courses_ranked_by(similarities)
    return RecommendCourses(
        search,
        repository,
        analyzer or FakeOccupationAnalyzer({"職業": PROFILE}),
        selector,
        limit,
    )


def test_core_courses_come_first_and_each_group_keeps_the_search_order() -> None:
    selector = FakeCourseSelector(
        [
            CourseChoice("科目C", Relevance.FOUNDATION, "理由C", "科目D"),
            CourseChoice("科目D", Relevance.CORE, "理由D"),
            CourseChoice("科目A", Relevance.FOUNDATION, "理由A", "科目B"),
            CourseChoice("科目B", Relevance.CORE, "理由B"),
        ]
    )
    similarities = {"科目A": 0.9, "科目B": 0.8, "科目C": 0.7, "科目D": 0.6, "科目E": 0.5}

    recommendation = recommend_over(similarities, selector).run("職業", 2026, "情", ALL_SEMESTERS)

    assert recommendation == Recommendation(
        PROFILE,
        (
            RecommendedCourse("科目B", "10001", Relevance.CORE, "理由B"),
            RecommendedCourse("科目D", "10003", Relevance.CORE, "理由D"),
            RecommendedCourse("科目A", "10000", Relevance.FOUNDATION, "理由A", "科目B"),
            RecommendedCourse("科目C", "10002", Relevance.FOUNDATION, "理由C", "科目D"),
        ),
        ("科目A", "科目B", "科目C", "科目D", "科目E"),
    )


def test_selector_reads_the_top_candidates_with_their_syllabi() -> None:
    selector = FakeCourseSelector([])
    similarities = {"科目A": 0.9, "科目B": 0.8, "科目C": 0.7}

    recommendation = recommend_over(similarities, selector, limit=2).run(
        "職業", 2026, "情", ALL_SEMESTERS
    )

    [(profile, candidates)] = selector.calls
    assert profile == PROFILE
    assert [(candidate.name, candidate.syllabus.code) for candidate in candidates] == [
        ("科目A", "10000"),
        ("科目B", "10001"),
    ]
    assert (recommendation.courses, recommendation.candidates) == ((), ("科目A", "科目B"))


def test_a_course_first_for_one_skill_reaches_the_selector_beside_the_whole_query() -> None:
    names = {"10000": "科目A", "10001": "科目B", "10002": "科目C"}
    repository = FakeCourseRepository(
        sections=tuple(replace(course_section(code), name=name) for code, name in names.items()),
        syllabi=tuple(syllabus(code) for code in names),
    )
    chunks = FakeChunkSearch(
        [
            ChunkHit("10000", ChunkSection.OVERVIEW, 0.9),
            ChunkHit("10001", ChunkSection.OVERVIEW, 0.8),
            ChunkHit("10002", ChunkSection.OVERVIEW, 0.1),
        ],
        hits_by_length={1.0: [ChunkHit("10002", ChunkSection.OVERVIEW, 0.9)]},
    )
    recommend = RecommendCourses(
        SearchCourses(repository, chunks, FakeEmbedder(), query_and_skills),
        repository,
        FakeOccupationAnalyzer({"職業": PROFILE}),
        FakeCourseSelector([]),
        2,
    )

    recommendation = recommend.run("職業", 2026, "情", ALL_SEMESTERS)

    assert recommendation.candidates == ("科目A", "科目C")


def test_a_course_outside_the_candidates_is_an_error() -> None:
    selector = FakeCourseSelector([CourseChoice("読ませていない科目", Relevance.CORE, "理由")])

    with pytest.raises(RecommendationError, match="候補に無い科目が選ばれています: 読ませて"):
        recommend_over({"科目A": 0.9}, selector).run("職業", 2026, "情", ALL_SEMESTERS)


def test_the_llm_is_not_called_when_there_are_no_candidates() -> None:
    analyzer = FakeOccupationAnalyzer({"職業": PROFILE})
    selector = FakeCourseSelector([])

    with pytest.raises(SearchError, match="候補の科目がありません"):
        recommend_over({"科目A": 0.9}, selector, analyzer).run("職業", 2026, "機", ALL_SEMESTERS)
    assert (analyzer.calls, selector.calls) == ([], [])


def test_selector_is_skipped_when_no_chunk_is_found() -> None:
    repository = FakeCourseRepository(
        sections=(course_section("10000"),), syllabi=(syllabus("10000"),)
    )
    search = SearchCourses(repository, FakeChunkSearch([]), FakeEmbedder(), query_and_skills)
    selector = FakeCourseSelector([])
    analyzer = FakeOccupationAnalyzer({"職業": PROFILE})

    recommendation = RecommendCourses(search, repository, analyzer, selector, 30).run(
        "職業", 2026, "情", ALL_SEMESTERS
    )

    assert recommendation == Recommendation(PROFILE, (), ())
    assert selector.calls == []


def test_a_ranked_course_whose_syllabus_is_missing_is_a_search_error() -> None:
    class MissingSyllabi(FakeCourseRepository):
        def syllabi_of(self, year: int, primary_codes: Set[str]) -> dict[str, Syllabus]:
            return {}

    repository, _ = courses_ranked_by({"科目A": 0.9})
    missing = MissingSyllabi(tuple(repository.stored_sections), tuple(repository.stored_syllabi))
    search = SearchCourses(
        missing,
        FakeChunkSearch([ChunkHit("10000", ChunkSection.OVERVIEW, 0.9)]),
        FakeEmbedder(),
        query_and_skills,
    )
    recommend = RecommendCourses(
        search, missing, FakeOccupationAnalyzer({"職業": PROFILE}), FakeCourseSelector([]), 30
    )

    with pytest.raises(SearchError, match="シラバスが DB にありません: 10000"):
        recommend.run("職業", 2026, "情", ALL_SEMESTERS)


def test_steps_are_reported_after_the_occupation_is_read_and_before_the_llm_selects() -> None:
    analyzer = FakeOccupationAnalyzer({"職業": PROFILE})
    selector = FakeCourseSelector([CourseChoice("科目A", Relevance.CORE, "理由A")])
    events: list[tuple[RecommendStep, int, int]] = []

    recommend_over({"科目A": 0.9}, selector, analyzer).run(
        "職業",
        2026,
        "情",
        ALL_SEMESTERS,
        lambda step: events.append((step, len(analyzer.calls), len(selector.calls))),
    )

    assert events == [(RecommendStep.SEARCHING, 1, 0), (RecommendStep.SELECTING, 1, 0)]


def test_selecting_is_not_reported_when_nothing_is_found() -> None:
    repository = FakeCourseRepository(
        sections=(course_section("10000"),), syllabi=(syllabus("10000"),)
    )
    search = SearchCourses(repository, FakeChunkSearch([]), FakeEmbedder(), query_and_skills)
    analyzer = FakeOccupationAnalyzer({"職業": PROFILE})
    steps: list[RecommendStep] = []

    RecommendCourses(search, repository, analyzer, FakeCourseSelector([]), 30).run(
        "職業", 2026, "情", ALL_SEMESTERS, steps.append
    )

    assert steps == [RecommendStep.SEARCHING]
