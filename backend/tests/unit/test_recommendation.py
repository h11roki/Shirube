import pytest

from app.domain.chunk import ChunkSection
from app.domain.occupation import OccupationProfile
from app.domain.ranking import CourseMatch
from app.domain.recommendation import (
    CourseChoice,
    Recommendation,
    RecommendationError,
    RecommendedCourse,
    Relevance,
    arrange,
)

PROFILE = OccupationProfile("職業", "職業", None, ("甲", "乙", "丙"))


def test_choice_without_a_reason_is_rejected() -> None:
    with pytest.raises(RecommendationError, match="科目A: 理由が空です"):
        CourseChoice("科目A", Relevance.CORE, " ")


def test_recommendation_with_the_same_course_twice_is_rejected() -> None:
    course = RecommendedCourse("科目A", "10000", Relevance.CORE, "理由")

    with pytest.raises(RecommendationError, match="同じ科目が 2 回選ばれています: 科目A"):
        Recommendation(PROFILE, (course, course), ("科目A",))


def test_recommendation_of_a_course_that_was_not_a_candidate_is_rejected() -> None:
    course = RecommendedCourse("科目Z", "10000", Relevance.CORE, "理由")

    with pytest.raises(RecommendationError, match="候補に無い科目が選ばれています: 科目Z"):
        Recommendation(PROFILE, (course,), ("科目A",))


def test_arrange_puts_core_before_foundation_and_keeps_the_search_order() -> None:
    matches = [
        CourseMatch(name, 1.0 - rank / 10, f"1000{rank}", ChunkSection.OVERVIEW)
        for rank, name in enumerate(["科目A", "科目B", "科目C", "科目D"])
    ]
    choices = [
        CourseChoice("科目D", Relevance.FOUNDATION, "理由D"),
        CourseChoice("科目C", Relevance.CORE, "理由C"),
        CourseChoice("科目A", Relevance.FOUNDATION, "理由A"),
    ]

    recommendation = arrange(PROFILE, matches, choices)

    assert recommendation.courses == (
        RecommendedCourse("科目C", "10002", Relevance.CORE, "理由C"),
        RecommendedCourse("科目A", "10000", Relevance.FOUNDATION, "理由A"),
        RecommendedCourse("科目D", "10003", Relevance.FOUNDATION, "理由D"),
    )
    assert recommendation.candidates == ("科目A", "科目B", "科目C", "科目D")


def test_arrange_keeps_one_choice_per_course_preferring_core_then_the_first() -> None:
    matches = [
        CourseMatch("科目A", 0.9, "10000", ChunkSection.OVERVIEW),
        CourseMatch("科目B", 0.8, "10001", ChunkSection.OVERVIEW),
    ]
    choices = [
        CourseChoice("科目A", Relevance.FOUNDATION, "土台としての理由"),
        CourseChoice("科目B", Relevance.FOUNDATION, "先の理由"),
        CourseChoice("科目A", Relevance.CORE, "中心としての理由"),
        CourseChoice("科目B", Relevance.FOUNDATION, "後の理由"),
    ]

    assert arrange(PROFILE, matches, choices).courses == (
        RecommendedCourse("科目A", "10000", Relevance.CORE, "中心としての理由"),
        RecommendedCourse("科目B", "10001", Relevance.FOUNDATION, "先の理由"),
    )


def test_arrange_rejects_a_choice_outside_the_matches() -> None:
    matches = [CourseMatch("科目A", 0.9, "10000", ChunkSection.OVERVIEW)]

    with pytest.raises(RecommendationError, match="候補に無い科目が選ばれています: 科目Z"):
        arrange(PROFILE, matches, [CourseChoice("科目Z", Relevance.CORE, "理由")])
