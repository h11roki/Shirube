from app.domain.chunk import ChunkSection
from app.domain.ranking import ChunkHit, CourseMatch, rank_courses, take_turns


def test_course_scores_its_best_chunk_across_every_class_page() -> None:
    hits = [
        ChunkHit("10001", ChunkSection.OVERVIEW, 0.40),
        ChunkHit("10001", ChunkSection.SCHEDULE, 0.70),
        ChunkHit("10002", ChunkSection.OBJECTIVES, 0.80),
        ChunkHit("20001", ChunkSection.OVERVIEW, 0.75),
    ]
    names_of_page = {"10001": {"電子回路Ⅰ"}, "10002": {"電子回路Ⅰ"}, "20001": {"論理回路"}}

    ranked = rank_courses(hits, names_of_page, limit=10)

    assert ranked == [
        CourseMatch("電子回路Ⅰ", 0.80, "10002", ChunkSection.OBJECTIVES),
        CourseMatch("論理回路", 0.75, "20001", ChunkSection.OVERVIEW),
    ]


def test_a_cross_listed_page_counts_for_each_of_its_course_names() -> None:
    hits = [ChunkHit("16806", ChunkSection.OVERVIEW, 0.5)]

    ranked = rank_courses(hits, {"16806": {"国際平和交流セミナー", "平和人権"}}, limit=10)

    assert [match.name for match in ranked] == ["国際平和交流セミナー", "平和人権"]


def test_ranking_is_cut_at_the_limit_and_ignores_pages_outside_the_candidates() -> None:
    hits = [
        ChunkHit("10001", ChunkSection.OVERVIEW, 0.9),
        ChunkHit("10002", ChunkSection.OVERVIEW, 0.8),
        ChunkHit("99999", ChunkSection.OVERVIEW, 0.99),
    ]

    ranked = rank_courses(hits, {"10001": {"甲"}, "10002": {"乙"}}, limit=1)

    assert [match.name for match in ranked] == ["甲"]


def matches(*names: str) -> list[CourseMatch]:
    return [CourseMatch(name, 0.5, "10001", ChunkSection.OVERVIEW) for name in names]


def test_each_ranking_in_turn_gives_its_best_course_not_yet_taken() -> None:
    rankings = [matches("甲", "乙", "丙"), matches("乙", "丁"), matches("戊")]

    taken = take_turns(rankings, limit=10)

    assert [match.name for match in taken] == ["甲", "乙", "戊", "丙", "丁"]


def test_turns_stop_at_the_limit() -> None:
    rankings = [matches("甲", "乙", "丙"), matches("乙", "丁"), matches("戊")]

    assert [match.name for match in take_turns(rankings, limit=3)] == ["甲", "乙", "戊"]


def test_a_single_ranking_is_only_cut_at_the_limit() -> None:
    assert [match.name for match in take_turns([matches("甲", "乙", "丙")], limit=2)] == [
        "甲",
        "乙",
    ]


def test_no_ranking_takes_nothing() -> None:
    assert take_turns([], limit=20) == []
