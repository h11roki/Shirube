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
    majority,
    voted_choices,
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
    dropped_a = CourseChoice("科目A", FOUNDATION, "理由", "科目B")
    dropped_b = CourseChoice("科目B", FOUNDATION, "理由", "科目C")

    with pytest.raises(RecommendationError, match="同じ科目が 2 回入っています: 科目A"):
        Recommendation(PROFILE, (course, course), ("科目A",))
    with pytest.raises(RecommendationError, match="同じ科目が 2 回入っています: 科目A"):
        Recommendation(PROFILE, (course,), ("科目A", "科目B"), (dropped_a,))
    with pytest.raises(RecommendationError, match="同じ科目が 2 回入っています: 科目B"):
        Recommendation(PROFILE, (course,), ("科目A", "科目B"), (dropped_b, dropped_b))


@pytest.mark.parametrize(
    ("courses", "unlinked"),
    [
        ((RecommendedCourse("科目Z", "10000", CORE, "理由"),), ()),
        (
            (RecommendedCourse("科目A", "10000", CORE, "理由"),),
            (CourseChoice("科目Z", FOUNDATION, "理由", "科目Y"),),
        ),
    ],
    ids=["recommended", "unlinked"],
)
def test_recommendation_of_a_course_that_was_not_a_candidate_is_rejected(
    courses: tuple[RecommendedCourse, ...], unlinked: tuple[CourseChoice, ...]
) -> None:
    with pytest.raises(RecommendationError, match="候補に無い科目が選ばれています: 科目Z"):
        Recommendation(PROFILE, courses, ("科目A",), unlinked)


@pytest.mark.parametrize(
    ("dropped", "message"),
    [
        (CourseChoice("科目B", CORE, "理由"), "中心か中心につながる土台があります: 科目B"),
        (
            CourseChoice("科目B", FOUNDATION, "理由", "科目A"),
            "中心か中心につながる土台があります: 科目B",
        ),
        (
            CourseChoice("科目B", FOUNDATION, "理由", "科目Z"),
            "候補に無い科目を前提にしています: 科目Z",
        ),
    ],
    ids=["core", "linked-to-core", "pointing-outside"],
)
def test_recommendation_drops_only_foundations_that_point_at_a_candidate_outside_the_core(
    dropped: CourseChoice, message: str
) -> None:
    core = RecommendedCourse("科目A", "10000", CORE, "理由")

    with pytest.raises(RecommendationError, match=message):
        Recommendation(PROFILE, (core,), ("科目A", "科目B"), (dropped,))


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
    assert recommendation.unlinked == (
        CourseChoice("科目C", FOUNDATION, "土台の科目の前提", "科目D"),
        CourseChoice("科目E", FOUNDATION, "自分の前提", "科目E"),
    )


def test_arrange_without_core_courses_drops_every_foundation() -> None:
    choices = [CourseChoice("科目A", FOUNDATION, "理由A", "科目B")]

    recommendation = arrange(PROFILE, matches_of("科目A", "科目B"), choices)

    assert (recommendation.courses, recommendation.unlinked) == ((), tuple(choices))


@pytest.mark.parametrize(
    "choice",
    [
        CourseChoice("科目Z", CORE, "理由"),
        CourseChoice("科目A", FOUNDATION, "理由", "科目Z"),
    ],
    ids=["course", "prerequisite"],
)
def test_arrange_rejects_a_choice_outside_the_matches(choice: CourseChoice) -> None:
    with pytest.raises(RecommendationError, match="候補に無い科目.*: 科目Z"):
        arrange(PROFILE, matches_of("科目A"), [choice])


def test_majority_keeps_courses_chosen_in_more_than_half_of_the_samples() -> None:
    samples = [
        [CourseChoice("科目A", CORE, "理由A"), CourseChoice("科目B", CORE, "理由B")],
        [CourseChoice("科目A", CORE, "理由A"), CourseChoice("科目C", CORE, "理由C")],
        [CourseChoice("科目A", CORE, "理由A"), CourseChoice("科目B", CORE, "理由B")],
    ]

    assert [choice.name for choice in voted_choices(samples, majority(len(samples)))] == [
        "科目A",
        "科目B",
    ]


def test_majority_needs_more_than_half_so_a_tie_between_two_samples_is_dropped() -> None:
    samples = [[CourseChoice("科目A", CORE, "理由A")], []]

    assert voted_choices(samples, majority(len(samples))) == []


def test_majority_takes_the_role_most_samples_gave_and_its_first_reason() -> None:
    samples = [
        [CourseChoice("科目B", FOUNDATION, "土台の理由", "科目A")],
        [CourseChoice("科目B", CORE, "中心の理由 1")],
        [CourseChoice("科目B", CORE, "中心の理由 2")],
    ]

    assert voted_choices(samples, majority(len(samples))) == [
        CourseChoice("科目B", CORE, "中心の理由 1")
    ]


def test_majority_breaks_an_even_split_between_roles_toward_foundation() -> None:
    samples = [
        [CourseChoice("科目B", CORE, "中心の理由")],
        [CourseChoice("科目B", FOUNDATION, "土台の理由", "科目A")],
        [CourseChoice("科目C", CORE, "理由C")],
        [CourseChoice("科目B", FOUNDATION, "土台の理由 2", "科目C")],
        [CourseChoice("科目B", CORE, "中心の理由 2")],
    ]

    assert voted_choices(samples, majority(len(samples))) == [
        CourseChoice("科目B", FOUNDATION, "土台の理由", "科目A")
    ]


def test_a_single_vote_keeps_every_course_any_sample_chose() -> None:
    samples = [
        [CourseChoice("科目A", CORE, "理由A")],
        [CourseChoice("科目A", CORE, "理由A"), CourseChoice("科目B", CORE, "理由B")],
        [CourseChoice("科目C", FOUNDATION, "理由C", "科目A")],
    ]

    assert [choice.name for choice in voted_choices(samples, 1)] == ["科目A", "科目B", "科目C"]


@pytest.mark.parametrize(("votes", "needed"), [(1, 1), (2, 2), (3, 2), (4, 3), (5, 3)])
def test_a_majority_is_more_than_half_of_the_votes(votes: int, needed: int) -> None:
    assert majority(votes) == needed


def test_majority_counts_a_course_listed_twice_in_one_sample_once() -> None:
    samples = [
        [CourseChoice("科目A", CORE, "理由A"), CourseChoice("科目A", CORE, "理由A")],
        [],
        [],
    ]

    assert voted_choices(samples, majority(len(samples))) == []


@pytest.mark.parametrize(
    "answer",
    [
        [
            CourseChoice("科目A", CORE, "理由A"),
            CourseChoice("科目B", FOUNDATION, "理由B", "科目C"),
            CourseChoice("科目B", FOUNDATION, "理由B'", "科目A"),
        ],
        [
            CourseChoice("科目B", FOUNDATION, "理由B", "科目A"),
            CourseChoice("科目A", CORE, "理由A"),
            CourseChoice("科目B", CORE, "理由B'"),
        ],
    ],
    ids=["linked-foundation-after-unlinked", "core-after-foundation"],
)
def test_the_same_answer_in_every_vote_arranges_like_a_single_answer(
    answer: list[CourseChoice],
) -> None:
    matches = matches_of("科目A", "科目B", "科目C")

    assert arrange(PROFILE, matches, voted_choices([answer] * 3, majority(3))) == arrange(
        PROFILE, matches, answer
    )
