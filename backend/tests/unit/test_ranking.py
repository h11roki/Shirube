from app.domain.chunk import ChunkSection
from app.domain.ranking import ChunkHit, CourseMatch, rank_courses


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
