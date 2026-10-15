from dataclasses import replace

import pytest

from app.application.search_courses import SearchCourses, SearchError
from app.domain.chunk import ChunkSection
from app.domain.course import ALL_GRADES
from app.domain.ranking import ChunkHit
from app.domain.syllabus import CourseName
from tests.builders import course_section, syllabus
from tests.fakes import FAKE_MODEL, FakeChunkSearch, FakeCourseRepository, FakeEmbedder

HITS = [
    ChunkHit("10001", ChunkSection.OVERVIEW, 0.6),
    ChunkHit("20001", ChunkSection.OVERVIEW, 0.9),
    ChunkHit("30001", ChunkSection.SCHEDULE, 0.7),
]


def courses() -> FakeCourseRepository:
    return FakeCourseRepository(
        sections=(
            replace(course_section("10001"), name="電子回路Ⅰ"),
            replace(course_section("10002"), name="電子回路Ⅰ"),
            replace(course_section("20001", departments=frozenset({"機"})), name="機械工学"),
            replace(course_section("30001"), name="論理回路"),
            replace(course_section("40001"), name="シラバスの無い科目"),
        ),
        syllabi=(
            syllabus("10001", aliases=(CourseName("10002", "電子回路Ⅰ(6U)"),)),
            syllabus("20001"),
            syllabus("30001"),
        ),
    )


def test_queries_are_embedded_at_once_and_searched_among_candidate_pages() -> None:
    chunks = FakeChunkSearch(HITS)
    embedder = FakeEmbedder()

    rankings = SearchCourses(courses(), chunks, embedder).run(
        2026, ["回路の設計", "論理"], "情", ALL_GRADES, 10
    )

    assert embedder.calls == [["回路の設計", "論理"]]
    assert chunks.calls == [
        (2026, FAKE_MODEL, [5.0], {"10001", "30001"}),
        (2026, FAKE_MODEL, [2.0], {"10001", "30001"}),
    ]
    assert [(match.name, match.similarity) for match in rankings[0]] == [
        ("論理回路", 0.7),
        ("電子回路Ⅰ", 0.6),
    ]
    assert len(rankings) == 2


def test_candidates_are_course_names_that_have_a_syllabus() -> None:
    search = SearchCourses(courses(), FakeChunkSearch([]), FakeEmbedder())

    assert search.candidates(2026, "情", ALL_GRADES) == {"電子回路Ⅰ", "論理回路"}


def test_no_candidates_means_no_embedding_call() -> None:
    embedder = FakeEmbedder()

    rankings = SearchCourses(courses(), FakeChunkSearch(HITS), embedder).run(
        2026, ["回路"], "情", frozenset(), 10
    )

    assert rankings == [[]]
    assert embedder.calls == []


def test_year_not_embedded_with_the_model_is_an_error_instead_of_empty_results() -> None:
    embedder = FakeEmbedder()
    search = SearchCourses(courses(), FakeChunkSearch(HITS, years_not_embedded=(2026,)), embedder)

    with pytest.raises(SearchError, match="2026 年度のシラバスがモデル fake-embedding で"):
        search.run(2026, ["回路"], "情", ALL_GRADES, 10)
    assert embedder.calls == []


def test_vectors_that_do_not_match_the_queries_are_an_error() -> None:
    class ShortEmbedder(FakeEmbedder):
        def embed(self, texts: list[str]) -> list[list[float]]:
            return super().embed(texts)[1:]

    search = SearchCourses(courses(), FakeChunkSearch(HITS), ShortEmbedder())

    with pytest.raises(SearchError, match="埋め込み 1 件がクエリ 2 件と合いません"):
        search.run(2026, ["回路", "論理"], "情", ALL_GRADES, 10)
