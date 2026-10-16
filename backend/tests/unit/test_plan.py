from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest

from app.domain.course import Term
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan, PlanConditions, PlanError
from app.domain.recommendation import Recommendation, RecommendedCourse, Relevance
from app.domain.roadmap import (
    PlacedCourse,
    Roadmap,
    Semester,
    SemesterPlan,
    remaining_semesters,
    term_on,
)
from tests.builders import course_section

PROFILE = OccupationProfile("職業", "職業", None, ("甲", "乙", "丙"))
START = Semester(3, Term.SPRING)
CONDITIONS = PlanConditions("職業", "情", 2026, START, (), 16)


@pytest.mark.parametrize(
    ("day", "term"),
    [
        (date(2026, 4, 1), Term.SPRING),
        (date(2026, 8, 31), Term.SPRING),
        (date(2026, 9, 1), Term.AUTUMN),
        (date(2027, 1, 15), Term.AUTUMN),
        (date(2027, 3, 31), Term.AUTUMN),
    ],
)
def test_the_term_is_spring_from_april_to_august_and_autumn_otherwise(
    day: date, term: Term
) -> None:
    assert term_on(day) is term


def roadmap_from(
    start: Semester,
    placed: tuple[PlacedCourse, ...] = (),
    unplaced: tuple[RecommendedCourse, ...] = (),
) -> Roadmap:
    semesters = remaining_semesters(start)
    return Roadmap(
        (
            SemesterPlan(semesters[0], placed),
            *(SemesterPlan(semester, ()) for semester in semesters[1:]),
        ),
        unplaced,
    )


def test_plan_keeps_its_conditions_with_the_matching_recommendation_and_roadmap() -> None:
    plan = Plan(uuid4(), CONDITIONS, Recommendation(PROFILE, (), ()), roadmap_from(START))

    assert [semester_plan.semester for semester_plan in plan.roadmap.semesters] == [
        START,
        Semester(3, Term.AUTUMN),
        Semester(4, Term.SPRING),
        Semester(4, Term.AUTUMN),
    ]


def test_plan_for_another_occupation_is_rejected() -> None:
    other = OccupationProfile("別の職業", "別の職業", None, ("甲", "乙", "丙"))

    with pytest.raises(PlanError, match="推薦の職業が条件と違います: 別の職業"):
        Plan(uuid4(), CONDITIONS, Recommendation(other, (), ()), roadmap_from(START))


def test_plan_whose_roadmap_does_not_run_from_the_start_to_the_last_semester_is_rejected() -> None:
    later = roadmap_from(Semester(3, Term.AUTUMN))
    shortened = Roadmap(roadmap_from(START).semesters[:2], ())

    for roadmap in (later, shortened):
        with pytest.raises(PlanError, match="道標の学期が 3 回生 春学期から 4 回生 秋学期まで"):
            Plan(uuid4(), CONDITIONS, Recommendation(PROFILE, (), ()), roadmap)


def test_plan_needs_every_recommended_course_placed_or_unplaced_once() -> None:
    course = RecommendedCourse("科目A", "10000", Relevance.CORE, "理由")
    recommendation = Recommendation(PROFILE, (course,), ("科目A",))

    with pytest.raises(PlanError, match="推薦の科目が、置いた科目か置けなかった科目に"):
        Plan(uuid4(), CONDITIONS, recommendation, roadmap_from(START))


def test_plan_with_a_semester_over_the_credit_limit_is_rejected() -> None:
    course = RecommendedCourse("科目A", "10000", Relevance.CORE, "理由")
    recommendation = Recommendation(PROFILE, (course,), ("科目A",))
    placed = PlacedCourse(course, replace(course_section("10000"), name="科目A"), True)
    conditions = replace(CONDITIONS, credit_limit=1)

    with pytest.raises(PlanError, match="単位の上限を超えた学期があります: 3 回生 春学期"):
        Plan(uuid4(), conditions, recommendation, roadmap_from(START, (placed,)))


@pytest.mark.parametrize(
    "chosen",
    [(("科目B", "6T"), ("科目A", "6A")), (("科目A", "6A"), ("科目A", "6T"))],
    ids=["unsorted", "repeated"],
)
def test_class_choices_are_sorted_by_course_and_one_per_course(
    chosen: tuple[tuple[str, str], ...],
) -> None:
    with pytest.raises(PlanError, match="クラスの選択は科目名の順に"):
        PlanConditions("職業", "情", 2026, START, chosen, 16)
