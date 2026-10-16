from datetime import date
from uuid import uuid4

import pytest

from app.domain.course import Term
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan, PlanConditions, PlanError
from app.domain.recommendation import Recommendation
from app.domain.roadmap import Roadmap, Semester, SemesterPlan, term_on

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


def roadmap_from(semester: Semester) -> Roadmap:
    return Roadmap((SemesterPlan(semester, ()),), ())


def test_plan_keeps_its_conditions_with_the_matching_recommendation_and_roadmap() -> None:
    plan = Plan(uuid4(), CONDITIONS, Recommendation(PROFILE, (), ()), roadmap_from(START))

    assert plan.roadmap.semesters[0].semester == plan.conditions.start


def test_plan_for_another_occupation_is_rejected() -> None:
    other = OccupationProfile("別の職業", "別の職業", None, ("甲", "乙", "丙"))

    with pytest.raises(PlanError, match="推薦の職業が条件と違います: 別の職業"):
        Plan(uuid4(), CONDITIONS, Recommendation(other, (), ()), roadmap_from(START))


def test_plan_whose_roadmap_starts_elsewhere_is_rejected() -> None:
    later = Semester(3, Term.AUTUMN)

    with pytest.raises(PlanError, match="道標が始める学期から始まっていません"):
        Plan(uuid4(), CONDITIONS, Recommendation(PROFILE, (), ()), roadmap_from(later))


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
