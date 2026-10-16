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


CORE, FOUNDATION = Relevance.CORE, Relevance.FOUNDATION


def matches_of(*names: str) -> list[CourseMatch]:
    return [
        CourseMatch(name, 1.0 - rank / 10, f"1000{rank}", ChunkSection.OVERVIEW)
        for rank, name in enumerate(names)
    ]


def test_choice_without_a_reason_is_rejected() -> None:
    with pytest.raises(RecommendationError, match="科目A: 理由が空です"):
        CourseChoice("科目A", CORE, " ")


@pytest.mark.parametrize(
    ("relevance", "prerequisite_for", "message"),
    [
        (CORE, "科目B", "科目A: 中心の科目が前提にする科目を指しています"),
        (FOUNDATION, None, "科目A: 土台の科目が前提にする中心の科目を指していません"),
    ],
    ids=["core-with-a-link", "foundation-without-a-link"],
)
def test_only_foundations_point_at_the_core_course_they_prepare_for(
    relevance: Relevance, prerequisite_for: str | None, message: str
) -> None:
    with pytest.raises(RecommendationError, match=message):
        CourseChoice("科目A", relevance, "理由", prerequisite_for)
    with pytest.raises(RecommendationError, match=message):
        RecommendedCourse("科目A", "10000", relevance, "理由", prerequisite_for)


def test_recommendation_with_the_same_course_twice_or_also_unlinked_is_rejected() -> None:
    course = RecommendedCourse("科目A", "10000", CORE, "理由")

    with pytest.raises(RecommendationError, match="同じ科目が 2 回入っています: 科目A"):
        Recommendation(PROFILE, (course, course), ("科目A",))
    with pytest.raises(RecommendationError, match="同じ科目が 2 回入っています: 科目A"):
        Recommendation(PROFILE, (course,), ("科目A",), ("科目A",))
    with pytest.raises(RecommendationError, match="同じ科目が 2 回入っています: 科目B"):
        Recommendation(PROFILE, (course,), ("科目A", "科目B"), ("科目B", "科目B"))


@pytest.mark.parametrize(
    ("courses", "unlinked"),
    [
        ((RecommendedCourse("科目Z", "10000", CORE, "理由"),), ()),
        ((RecommendedCourse("科目A", "10000", CORE, "理由"),), ("科目Z",)),
    ],
    ids=["recommended", "unlinked"],
)
def test_recommendation_of_a_course_that_was_not_a_candidate_is_rejected(
    courses: tuple[RecommendedCourse, ...], unlinked: tuple[str, ...]
) -> None:
    with pytest.raises(RecommendationError, match="候補に無い科目が選ばれています: 科目Z"):
        Recommendation(PROFILE, courses, ("科目A",), unlinked)


def test_recommendation_with_a_foundation_for_a_course_that_is_not_core_is_rejected() -> None:
    courses = (
        RecommendedCourse("科目A", "10000", CORE, "理由A"),
        RecommendedCourse("科目B", "10001", FOUNDATION, "理由B", "科目C"),
        RecommendedCourse("科目C", "10002", FOUNDATION, "理由C", "科目A"),
    )

    with pytest.raises(RecommendationError, match="前提にする土台があります: 科目B"):
        Recommendation(PROFILE, courses, ("科目A", "科目B", "科目C"))


def test_arrange_puts_core_before_foundation_and_keeps_the_search_order() -> None:
    choices = [
        CourseChoice("科目D", FOUNDATION, "理由D", "科目C"),
        CourseChoice("科目C", CORE, "理由C"),
        CourseChoice("科目A", FOUNDATION, "理由A", "科目C"),
    ]

    recommendation = arrange(PROFILE, matches_of("科目A", "科目B", "科目C", "科目D"), choices)

    assert recommendation == Recommendation(
        PROFILE,
        (
            RecommendedCourse("科目C", "10002", CORE, "理由C"),
            RecommendedCourse("科目A", "10000", FOUNDATION, "理由A", "科目C"),
            RecommendedCourse("科目D", "10003", FOUNDATION, "理由D", "科目C"),
        ),
        ("科目A", "科目B", "科目C", "科目D"),
    )


def test_arrange_keeps_one_choice_per_course_preferring_core_then_the_first() -> None:
    choices = [
        CourseChoice("科目A", CORE, "先の中心の理由"),
        CourseChoice("科目B", FOUNDATION, "先の理由", "科目A"),
        CourseChoice("科目C", FOUNDATION, "土台としての理由", "科目A"),
        CourseChoice("科目C", CORE, "中心としての理由"),
        CourseChoice("科目A", CORE, "後の中心の理由"),
        CourseChoice("科目B", FOUNDATION, "後の理由", "科目C"),
    ]

    assert arrange(PROFILE, matches_of("科目A", "科目B", "科目C"), choices).courses == (
        RecommendedCourse("科目A", "10000", CORE, "先の中心の理由"),
        RecommendedCourse("科目C", "10002", CORE, "中心としての理由"),
        RecommendedCourse("科目B", "10001", FOUNDATION, "先の理由", "科目A"),
    )


def test_arrange_drops_foundations_for_courses_not_chosen_as_core() -> None:
    choices = [
        CourseChoice("科目A", CORE, "理由A"),
        CourseChoice("科目D", FOUNDATION, "中心でない科目の前提", "科目B"),
        CourseChoice("科目B", FOUNDATION, "理由B", "科目A"),
        CourseChoice("科目C", FOUNDATION, "土台の科目の前提", "科目D"),
        CourseChoice("科目D", FOUNDATION, "理由D", "科目A"),
        CourseChoice("科目E", FOUNDATION, "自分の前提", "科目E"),
        CourseChoice("科目B", FOUNDATION, "後で外れる理由", "科目C"),
    ]

    recommendation = arrange(
        PROFILE, matches_of("科目A", "科目B", "科目C", "科目D", "科目E"), choices
    )

    assert recommendation.courses == (
        RecommendedCourse("科目A", "10000", CORE, "理由A"),
        RecommendedCourse("科目B", "10001", FOUNDATION, "理由B", "科目A"),
        RecommendedCourse("科目D", "10003", FOUNDATION, "理由D", "科目A"),
    )
    assert recommendation.unlinked == ("科目C", "科目E")


def test_arrange_without_core_courses_drops_every_foundation() -> None:
    choices = [CourseChoice("科目A", FOUNDATION, "理由A", "科目B")]

    recommendation = arrange(PROFILE, matches_of("科目A", "科目B"), choices)

    assert (recommendation.courses, recommendation.unlinked) == ((), ("科目A",))


@pytest.mark.parametrize(
    "choice",
    [
        CourseChoice("科目Z", CORE, "理由"),
        CourseChoice("科目A", FOUNDATION, "理由", "科目Z"),
    ],
    ids=["course", "prerequisite"],
)
def test_arrange_rejects_a_choice_outside_the_matches(choice: CourseChoice) -> None:
    with pytest.raises(RecommendationError, match="候補に無い科目が選ばれています: 科目Z"):
        arrange(PROFILE, matches_of("科目A"), [choice])
