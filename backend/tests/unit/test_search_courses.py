from dataclasses import replace

import pytest

from app.application.search_courses import NoCandidatesError, SearchCourses, SearchError
from app.domain.chunk import ChunkSection
from app.domain.course import Term
from app.domain.ranking import ChunkHit
from app.domain.roadmap import ALL_SEMESTERS, Semester
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


def test_candidates_are_course_names_offered_to_the_student_that_have_a_syllabus() -> None:
    candidates = SearchCourses(courses(), FakeChunkSearch([]), FakeEmbedder()).candidates(
        2026, "情", ALL_SEMESTERS
    )

    assert candidates.names == {"電子回路Ⅰ", "論理回路"}


def test_candidates_open_in_one_of_the_given_semesters() -> None:
    search = SearchCourses(courses(), FakeChunkSearch([]), FakeEmbedder())
    autumns = (Semester(3, Term.AUTUMN), Semester(4, Term.AUTUMN))

    assert search.candidates(2026, "情", (Semester(4, Term.SPRING),)).names == {
        "電子回路Ⅰ",
        "論理回路",
    }
    with pytest.raises(SearchError, match="候補の科目がありません"):
        search.candidates(2026, "情", autumns)


def test_queries_are_embedded_at_once_and_each_is_ranked_by_its_own_vector() -> None:
    chunks = FakeChunkSearch(
        [],
        hits_by_length={
            5.0: [ChunkHit("10001", ChunkSection.OVERVIEW, 0.6), *HITS[1:]],
            2.0: [ChunkHit("10001", ChunkSection.OVERVIEW, 0.9), *HITS[1:]],
        },
    )
    embedder = FakeEmbedder()
    candidates = SearchCourses(courses(), chunks, embedder).candidates(2026, "情", ALL_SEMESTERS)

    rankings = candidates.rank(["回路の設計", "論理"], 10)

    assert embedder.calls == [["回路の設計", "論理"]]
    assert [call[1:] for call in chunks.calls] == [
        (FAKE_MODEL, [5.0], {"10001", "30001"}),
        (FAKE_MODEL, [2.0], {"10001", "30001"}),
    ]
    assert [match.name for match in rankings[0]] == ["論理回路", "電子回路Ⅰ"]
    assert [match.name for match in rankings[1]] == ["電子回路Ⅰ", "論理回路"]


def test_no_candidates_is_an_error_instead_of_empty_results() -> None:
    search = SearchCourses(courses(), FakeChunkSearch(HITS), FakeEmbedder())

    with pytest.raises(SearchError, match="候補の科目がありません"):
        search.candidates(2026, "情", ())


def test_year_not_embedded_with_the_model_is_an_error_instead_of_empty_results() -> None:
    search = SearchCourses(courses(), FakeChunkSearch(HITS, embedded=False), FakeEmbedder())

    with pytest.raises(SearchError, match="2026 年度のシラバスがモデル fake-embedding で"):
        search.candidates(2026, "情", ALL_SEMESTERS)


def test_vectors_that_do_not_match_the_queries_are_an_error() -> None:
    class ShortEmbedder(FakeEmbedder):
        def embed(self, texts: list[str]) -> list[list[float]]:
            return super().embed(texts)[1:]

    candidates = SearchCourses(courses(), FakeChunkSearch(HITS), ShortEmbedder()).candidates(
        2026, "情", ALL_SEMESTERS
    )

    with pytest.raises(SearchError, match="埋め込み 1 件がクエリ 2 件と合いません"):
        candidates.rank(["回路", "論理"], 10)


def test_a_year_without_timetable_or_syllabi_is_a_search_error_not_a_lack_of_candidates() -> None:
    search = SearchCourses(FakeCourseRepository(), FakeChunkSearch([]), FakeEmbedder())

    with pytest.raises(
        SearchError, match="2026 年度の時間割かシラバスが DB にありません"
    ) as raised:
        search.candidates(2026, "情", ALL_SEMESTERS)
    assert not isinstance(raised.value, NoCandidatesError)
