import pytest

from app.domain.occupation import OccupationProfile
from app.domain.recommendation import (
    CourseChoice,
    Recommendation,
    RecommendationError,
    RecommendedCourse,
    Relevance,
)


def test_choice_without_a_reason_is_rejected() -> None:
    with pytest.raises(RecommendationError, match="科目A: 理由が空です"):
        CourseChoice("科目A", Relevance.CORE, " ")


def test_recommendation_with_the_same_course_twice_is_rejected() -> None:
    profile = OccupationProfile("職業", "職業", None, ("甲", "乙", "丙"))
    course = RecommendedCourse("科目A", "10000", Relevance.CORE, "理由")

    with pytest.raises(RecommendationError, match="同じ科目が 2 回選ばれています: 科目A"):
        Recommendation(profile, (course, course), 30)
