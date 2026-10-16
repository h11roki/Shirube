from dataclasses import replace

import pytest

from app.domain.course import Audience, CourseSection, Term, TimeSlot, Weekday
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import Recommendation, RecommendedCourse, Relevance
from app.domain.roadmap import (
    PlacedCourse,
    Roadmap,
    RoadmapError,
    Semester,
    SemesterPlan,
    place,
    remaining_semesters,
)
from tests.builders import course_section

PROFILE = OccupationProfile("職業", "職業", None, ("甲", "乙", "丙"))
SPRING_1 = (Semester(1, Term.SPRING),)
MON_1 = (TimeSlot(Weekday.MON, 1),)
TUE_1 = (TimeSlot(Weekday.TUE, 1),)


def section(
    code: str,
    name: str,
    term: Term | None = Term.SPRING,
    slots: tuple[TimeSlot, ...] = MON_1,
    class_code: str = "6T",
    departments: frozenset[str] | None = None,
    grades: frozenset[int] = frozenset({1, 2, 3, 4}),
    credits: int = 2,
) -> CourseSection:
    return replace(
        course_section(code, term, slots, departments),
        name=name,
        class_code=class_code,
        audiences=(Audience(2020, 2026, grades, "専門"),),
        credits=credits,
    )


def recommend(*names: str) -> Recommendation:
    courses = tuple(
        RecommendedCourse(name, "10000", Relevance.CORE, f"{name}の理由") for name in names
    )
    return Recommendation(PROFILE, courses, names)


def placed_names(plan: SemesterPlan) -> list[tuple[str, str | None]]:
    return [(placed.course.name, placed.section.class_code) for placed in plan.courses]


def test_remaining_semesters_run_from_now_to_the_autumn_of_the_fourth_grade() -> None:
    assert remaining_semesters(Semester(3, Term.AUTUMN)) == (
        Semester(3, Term.AUTUMN),
        Semester(4, Term.SPRING),
        Semester(4, Term.AUTUMN),
    )
    assert len(remaining_semesters(Semester(1, Term.SPRING))) == 8
    assert remaining_semesters(Semester(4, Term.AUTUMN)) == (Semester(4, Term.AUTUMN),)


def test_grade_outside_one_to_four_is_rejected() -> None:
    with pytest.raises(RoadmapError, match="回生は 1〜4"):
        remaining_semesters(Semester(5, Term.SPRING))


def test_earlier_courses_take_the_slot_and_later_ones_move_to_another_class_or_term() -> None:
    sections = [
        section("10000", "科目A"),
        section("10001", "科目B", class_code="X1"),
        section("10002", "科目B", class_code="X2", slots=TUE_1),
        section("10003", "科目C", term=Term.AUTUMN),
        section("10004", "科目D", class_code="Y1"),
        section("10005", "科目D", term=Term.AUTUMN, class_code="Y2", slots=TUE_1),
    ]
    semesters = (Semester(1, Term.SPRING), Semester(1, Term.AUTUMN))

    roadmap = place(
        recommend("科目A", "科目B", "科目C", "科目D"), sections, "情", 2026, semesters, 16, {}
    )

    spring, autumn = roadmap.semesters
    assert placed_names(spring) == [("科目A", "6T"), ("科目B", "X2")]
    assert placed_names(autumn) == [("科目C", "6T"), ("科目D", "Y2")]
    assert roadmap.unplaced == ()


def test_the_credit_limit_and_the_grade_keep_courses_out() -> None:
    sections = [
        section("10000", "科目A", credits=2),
        section("10001", "科目B", slots=TUE_1, credits=2),
        section("10002", "科目C", slots=(), grades=frozenset({2})),
    ]

    roadmap = place(recommend("科目A", "科目B", "科目C"), sections, "情", 2026, SPRING_1, 3, {})

    assert placed_names(roadmap.semesters[0]) == [("科目A", "6T")]
    assert [course.name for course in roadmap.unplaced] == ["科目B", "科目C"]


def test_courses_without_a_term_go_to_spring_and_without_slots_never_collide() -> None:
    sections = [
        section("10000", "通年の科目", term=None, slots=()),
        section("10001", "オンデマンドの科目", slots=()),
        section("10002", "科目A"),
    ]

    recommendation = recommend("通年の科目", "オンデマンドの科目", "科目A")

    roadmap = place(recommendation, sections, "情", 2026, SPRING_1, 16, {})

    assert [name for name, _ in placed_names(roadmap.semesters[0])] == [
        "通年の科目",
        "オンデマンドの科目",
        "科目A",
    ]


def test_classes_split_by_the_department_follow_the_users_choice() -> None:
    own = frozenset({"情"})
    sections = [
        section("10000", "情報科学Ⅱ", class_code="TA", departments=own),
        section("10001", "情報科学Ⅱ", class_code="TB", departments=own, slots=TUE_1),
    ]

    chosen = place(recommend("情報科学Ⅱ"), sections, "情", 2026, SPRING_1, 16, {"情報科学Ⅱ": "TB"})
    guessed = place(recommend("情報科学Ⅱ"), sections, "情", 2026, SPRING_1, 16, {})

    [chosen_class] = chosen.semesters[0].courses
    [guessed_class] = guessed.semesters[0].courses
    assert (chosen_class.section.class_code, chosen_class.class_confirmed) == ("TB", True)
    assert (guessed_class.section.class_code, guessed_class.class_confirmed) == ("TA", False)


@pytest.mark.parametrize(
    ("chosen", "message"),
    [
        ({"情報科学Ⅱ": "TZ"}, "情報科学Ⅱ: 選べるクラスは TA、TB です"),
        ({"情報科学Ⅱ": "TC"}, "情報科学Ⅱ: 選べるクラスは TA、TB です"),
    ],
    ids=["unknown-class", "other-departments-class"],
)
def test_choosing_a_class_that_cannot_be_chosen_is_rejected(
    chosen: dict[str, str], message: str
) -> None:
    own = frozenset({"情"})
    sections = [
        section("10000", "情報科学Ⅱ", class_code="TA", departments=own),
        section("10001", "情報科学Ⅱ", class_code="TB", departments=own, slots=TUE_1),
        section("10003", "情報科学Ⅱ", class_code="TC", departments=frozenset({"電"})),
        section("10002", "科目A"),
    ]

    with pytest.raises(RoadmapError, match=message):
        place(recommend("情報科学Ⅱ", "科目A"), sections, "情", 2026, SPRING_1, 16, chosen)


def test_a_semester_with_two_courses_in_one_slot_is_rejected() -> None:
    course = RecommendedCourse("科目A", "10000", Relevance.CORE, "理由")
    placed = PlacedCourse(course, section("10000", "科目A"), class_confirmed=True)

    with pytest.raises(RoadmapError, match="同じコマに 2 つの授業があります"):
        SemesterPlan(SPRING_1[0], (placed, placed))


def test_a_year_long_course_keeps_its_slot_in_the_autumn_of_the_same_grade() -> None:
    sections = [
        section("10000", "通年の科目", term=None),
        section("10001", "秋の科目", term=Term.AUTUMN),
    ]
    semesters = remaining_semesters(Semester(1, Term.SPRING))[:4]

    roadmap = place(recommend("通年の科目", "秋の科目"), sections, "情", 2026, semesters, 16, {})

    assert [[name for name, _ in placed_names(plan)] for plan in roadmap.semesters] == [
        ["通年の科目"],
        [],
        [],
        ["秋の科目"],
    ]
    first_autumn = roadmap.semesters[1]
    assert [placed.course.name for placed in first_autumn.continuing] == ["通年の科目"]
    assert first_autumn.credits == 0


def test_one_class_listed_in_two_rows_is_not_a_split_class() -> None:
    own = frozenset({"情"})
    sections = [
        section("10000", "情報処理", class_code="6T", departments=own),
        section("10001", "情報処理", class_code="6T", departments=own, term=Term.AUTUMN),
    ]

    roadmap = place(recommend("情報処理"), sections, "情", 2026, SPRING_1, 16, {})

    [placed] = roadmap.semesters[0].courses
    assert placed.class_confirmed


def test_a_roadmap_with_semesters_out_of_order_is_rejected() -> None:
    spring, autumn = remaining_semesters(Semester(1, Term.SPRING))[:2]

    with pytest.raises(RoadmapError, match="古い順に並べてください"):
        Roadmap((SemesterPlan(autumn, ()), SemesterPlan(spring, ())), ())
    with pytest.raises(RoadmapError, match="古い順に並べてください"):
        Roadmap((SemesterPlan(spring, ()), SemesterPlan(spring, ())), ())
    with pytest.raises(RoadmapError, match="回生は 1〜4"):
        Roadmap((SemesterPlan(Semester(5, Term.SPRING), ()),), ())


def test_choices_that_no_longer_apply_are_ignored() -> None:
    sections = [section("10000", "科目A")]
    stale = {"前回の科目": "TA", "科目A": "6T"}

    roadmap = place(recommend("科目A"), sections, "情", 2026, SPRING_1, 16, stale)

    assert placed_names(roadmap.semesters[0]) == [("科目A", "6T")]


def test_only_classes_open_to_the_users_remaining_grades_count_as_split() -> None:
    own = frozenset({"情"})
    sections = [
        section("10000", "情報科学Ⅱ", class_code="TA", departments=own, grades=frozenset({1})),
        section("10001", "情報科学Ⅱ", class_code="TB", departments=own, grades=frozenset({2})),
    ]
    semesters = remaining_semesters(Semester(2, Term.SPRING))

    roadmap = place(recommend("情報科学Ⅱ"), sections, "情", 2026, semesters, 16, {})

    [placed] = roadmap.semesters[0].courses
    assert (placed.section.class_code, placed.class_confirmed) == ("TB", True)


def test_an_unchosen_split_course_is_placed_only_in_a_class_of_the_users_department() -> None:
    own = frozenset({"情"})
    sections = [
        section("10000", "科目A"),
        section("10001", "情報科学Ⅱ", class_code="TA", departments=own),
        section("10002", "情報科学Ⅱ", class_code="TB", departments=own),
        section("10003", "情報科学Ⅱ", class_code="R1", slots=TUE_1),
    ]

    roadmap = place(recommend("科目A", "情報科学Ⅱ"), sections, "情", 2026, SPRING_1, 16, {})

    assert placed_names(roadmap.semesters[0]) == [("科目A", "6T")]
    assert [course.name for course in roadmap.unplaced] == ["情報科学Ⅱ"]


def test_classes_for_different_grades_are_not_split_classes() -> None:
    own = frozenset({"情"})
    sections = [
        section("10000", "情報科学Ⅱ", class_code="TA", departments=own, grades=frozenset({2})),
        section("10001", "情報科学Ⅱ", class_code="TB", departments=own, grades=frozenset({3, 4})),
    ]

    roadmap = place(
        recommend("情報科学Ⅱ"),
        sections,
        "情",
        2026,
        remaining_semesters(Semester(2, Term.SPRING)),
        16,
        {},
    )

    [placed] = roadmap.semesters[0].courses
    assert (placed.section.class_code, placed.class_confirmed) == ("TA", True)


def test_a_departments_own_class_that_never_opens_leaves_the_course_to_other_classes() -> None:
    sections = [
        section(
            "10000", "数学基礎", class_code="X", departments=frozenset({"情"}), grades=frozenset()
        ),
        section("10001", "数学基礎", class_code="TA"),
    ]

    roadmap = place(recommend("数学基礎"), sections, "情", 2026, SPRING_1, 16, {})

    assert placed_names(roadmap.semesters[0]) == [("数学基礎", "TA")]


def test_the_departments_own_class_is_preferred_over_a_class_for_all_departments() -> None:
    sections = [
        section("10000", "数学演習", class_code="A1", slots=TUE_1),
        section("10001", "数学演習", class_code="TA", departments=frozenset({"情"})),
    ]

    roadmap = place(recommend("数学演習"), sections, "情", 2026, SPRING_1, 16, {})

    assert placed_names(roadmap.semesters[0]) == [("数学演習", "TA")]


def test_a_class_without_a_code_can_be_chosen() -> None:
    own = frozenset({"情"})
    sections = [
        replace(section("10000", "情報科学Ⅱ", departments=own), class_code=None),
        section("10001", "情報科学Ⅱ", class_code="TA", departments=own, slots=TUE_1),
    ]

    roadmap = place(recommend("情報科学Ⅱ"), sections, "情", 2026, SPRING_1, 16, {"情報科学Ⅱ": ""})

    [placed] = roadmap.semesters[0].courses
    assert (placed.section.class_code, placed.class_confirmed) == (None, True)
    with pytest.raises(RoadmapError, match="選べるクラスは 記号なし、TA です"):
        place(recommend("情報科学Ⅱ"), sections, "情", 2026, SPRING_1, 16, {"情報科学Ⅱ": "TZ"})


def test_a_roadmap_breaking_its_promises_is_rejected() -> None:
    spring, autumn = remaining_semesters(Semester(1, Term.SPRING))[:2]
    course = RecommendedCourse("通年の科目", "10000", Relevance.CORE, "理由")
    year_long = PlacedCourse(course, section("10000", "通年の科目", term=None), True)
    other = PlacedCourse(course, section("10000", "通年の科目"), True)

    with pytest.raises(RoadmapError, match="続きの授業を持てるのは秋学期だけ"):
        SemesterPlan(spring, (), (year_long,))
    with pytest.raises(RoadmapError, match="春学期に置いていない続きの授業"):
        Roadmap((SemesterPlan(spring, (other,)), SemesterPlan(autumn, (), (year_long,))), ())
    with pytest.raises(RoadmapError, match="置けなかった科目にもあります: 通年の科目"):
        Roadmap((SemesterPlan(spring, (year_long,)),), (course,))
