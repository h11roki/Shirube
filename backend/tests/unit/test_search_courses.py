from dataclasses import dataclass, replace

import pytest

from app.application.ports import EmbeddingError
from app.application.search_courses import (
    NoCandidatesError,
    SearchCourses,
    SearchError,
    query_and_skills,
    whole_query,
)
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
    candidates = SearchCourses(
        courses(), FakeChunkSearch([]), FakeEmbedder(), query_and_skills
    ).candidates(2026, "情", ALL_SEMESTERS)

    assert candidates.names == {"電子回路Ⅰ", "論理回路"}


def test_candidates_open_in_one_of_the_given_semesters() -> None:
    search = SearchCourses(courses(), FakeChunkSearch([]), FakeEmbedder(), query_and_skills)
    autumns = (Semester(3, Term.AUTUMN), Semester(4, Term.AUTUMN))

    assert search.candidates(2026, "情", (Semester(4, Term.SPRING),)).names == {
        "電子回路Ⅰ",
        "論理回路",
    }
    with pytest.raises(SearchError, match="候補の科目がありません"):
        search.candidates(2026, "情", autumns)


def three_courses() -> FakeCourseRepository:
    names = {"10001": "甲", "10002": "乙", "10003": "丙"}
    return FakeCourseRepository(
        sections=tuple(replace(course_section(code), name=name) for code, name in names.items()),
        syllabi=tuple(syllabus(code) for code in names),
    )


def ranked_apart() -> FakeChunkSearch:
    return FakeChunkSearch(
        [],
        hits_by_length={
            6.0: [
                ChunkHit("10001", ChunkSection.OVERVIEW, 0.9),
                ChunkHit("10002", ChunkSection.OVERVIEW, 0.8),
                ChunkHit("10003", ChunkSection.OVERVIEW, 0.1),
            ],
            3.0: [
                ChunkHit("10003", ChunkSection.SCHEDULE, 0.9),
                ChunkHit("10001", ChunkSection.OVERVIEW, 0.2),
                ChunkHit("10002", ChunkSection.OVERVIEW, 0.1),
            ],
        },
    )


@dataclass(frozen=True)
class Target:
    query: str
    skills: tuple[str, ...]


def test_the_query_and_each_skill_take_turns_giving_their_best_course_not_yet_taken() -> None:
    chunks = ranked_apart()
    embedder = FakeEmbedder()
    candidates = SearchCourses(three_courses(), chunks, embedder, query_and_skills).candidates(
        2026, "情", ALL_SEMESTERS
    )

    picked = candidates.pick([Target("職業のクエリ", ("スキル",)), Target("スキル", ())], 2)

    assert embedder.calls == [["職業のクエリ", "スキル", "スキル"]]
    assert [call[1:] for call in chunks.calls] == [
        (FAKE_MODEL, [6.0], {"10001", "10002", "10003"}),
        (FAKE_MODEL, [3.0], {"10001", "10002", "10003"}),
        (FAKE_MODEL, [3.0], {"10001", "10002", "10003"}),
    ]
    assert [[match.name for match in matches] for matches in picked] == [
        ["甲", "丙"],
        ["丙", "甲"],
    ]


def test_without_the_skill_search_only_the_whole_query_ranks_the_candidates() -> None:
    embedder = FakeEmbedder()
    candidates = SearchCourses(three_courses(), ranked_apart(), embedder, whole_query).candidates(
        2026, "情", ALL_SEMESTERS
    )

    [matches] = candidates.pick([Target("職業のクエリ", ("スキル",))], 2)

    assert embedder.calls == [["職業のクエリ"]]
    assert [match.name for match in matches] == ["甲", "乙"]


def test_no_candidates_is_an_error_instead_of_empty_results() -> None:
    search = SearchCourses(courses(), FakeChunkSearch(HITS), FakeEmbedder(), query_and_skills)

    with pytest.raises(SearchError, match="候補の科目がありません"):
        search.candidates(2026, "情", ())


def test_year_not_embedded_with_the_model_is_an_error_instead_of_empty_results() -> None:
    search = SearchCourses(
        courses(), FakeChunkSearch(HITS, embedded=False), FakeEmbedder(), query_and_skills
    )

    with pytest.raises(SearchError, match="2026 年度のシラバスがモデル fake-embedding で"):
        search.candidates(2026, "情", ALL_SEMESTERS)


def test_vectors_that_do_not_match_the_queries_are_an_error() -> None:
    class ShortEmbedder(FakeEmbedder):
        def embed(self, texts: list[str]) -> list[list[float]]:
            return super().embed(texts)[1:]

    candidates = SearchCourses(
        courses(), FakeChunkSearch(HITS), ShortEmbedder(), query_and_skills
    ).candidates(2026, "情", ALL_SEMESTERS)

    with pytest.raises(EmbeddingError, match="埋め込み 1 件がクエリ 2 件と合いません"):
        candidates.pick([Target("回路", ("論理",))], 10)


def test_a_year_without_timetable_or_syllabi_is_a_search_error_not_a_lack_of_candidates() -> None:
    search = SearchCourses(
        FakeCourseRepository(), FakeChunkSearch([]), FakeEmbedder(), query_and_skills
    )

    with pytest.raises(
        SearchError, match="2026 年度の時間割かシラバスが DB にありません"
    ) as raised:
        search.candidates(2026, "情", ALL_SEMESTERS)
    assert not isinstance(raised.value, NoCandidatesError)


def test_a_taken_name_leaves_the_candidates_with_every_name_of_its_joint_page() -> None:
    joint = FakeCourseRepository(
        sections=(
            replace(course_section("50001"), name="合併の科目甲"),
            replace(course_section("50002"), name="合併の科目乙"),
            replace(course_section("30001"), name="論理回路"),
        ),
        syllabi=(
            syllabus("50001", aliases=(CourseName("50002", "合併の科目乙"),)),
            syllabus("30001"),
        ),
    )
    search = SearchCourses(joint, FakeChunkSearch([]), FakeEmbedder(), query_and_skills)

    assert search.candidates(2026, "情", ALL_SEMESTERS, {"合併の科目甲"}).names == {"論理回路"}
    with pytest.raises(NoCandidatesError, match="もう取ったと答えた授業は除いています"):
        search.candidates(2026, "情", ALL_SEMESTERS, {"合併の科目乙", "論理回路"})


def test_the_note_about_taken_courses_is_added_only_when_they_emptied_the_candidates() -> None:
    search = SearchCourses(courses(), FakeChunkSearch([]), FakeEmbedder(), query_and_skills)
    autumns = (Semester(3, Term.AUTUMN), Semester(4, Term.AUTUMN))

    with pytest.raises(NoCandidatesError) as unrelated:
        search.candidates(2026, "情", autumns, {"論理回路"})

    assert "除いています" not in str(unrelated.value)


def test_a_taken_name_from_another_department_does_not_remove_a_joint_page() -> None:
    joint = FakeCourseRepository(
        sections=(
            replace(course_section("70001", departments=frozenset({"機"})), name="機の科目"),
            replace(course_section("70002"), name="情も取れる別名"),
        ),
        syllabi=(syllabus("70001", aliases=(CourseName("70002", "情も取れる別名"),)),),
    )
    search = SearchCourses(joint, FakeChunkSearch([]), FakeEmbedder(), query_and_skills)

    assert search.candidates(2026, "情", ALL_SEMESTERS, {"機の科目"}).names == {"情も取れる別名"}
