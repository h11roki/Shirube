from dataclasses import replace
from uuid import UUID

import pytest

from app.application.create_plan import CreatePlan
from app.application.recommend_courses import RecommendCourses
from app.domain.course import Audience, Term, TimeSlot, Weekday
from app.domain.occupation import OccupationProfile
from app.domain.plan import PlanConditions
from app.domain.recommendation import CourseChoice, Relevance
from app.domain.roadmap import RoadmapError, Semester
from tests.fakes import (
    FakeCourseSelector,
    FakeOccupationAnalyzer,
    FakePlanRepository,
    courses_ranked_by,
)

PROFILE = OccupationProfile("職業", "解釈した職業", None, ("甲", "乙", "丙"))
START = Semester(3, Term.SPRING)
OWNER = UUID("6f1c2a9e-3b4d-4e5f-8a7b-9c0d1e2f3a4b")


def test_plan_recommends_from_the_start_grade_places_from_the_start_term_and_is_saved() -> None:
    repository, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8, "科目C": 0.7, "科目D": 0.6})
    first_grade_only = (Audience(2020, 2026, frozenset({1}), "専門"),)
    a, b, c, d = repository.stored_sections
    repository.stored_sections = [
        a,
        replace(b, slots=(TimeSlot(Weekday.TUE, 1),)),
        c,
        replace(d, audiences=first_grade_only),
    ]
    selector = FakeCourseSelector(
        [
            CourseChoice("科目A", Relevance.CORE, "理由A"),
            CourseChoice("科目B", Relevance.CORE, "理由B"),
            CourseChoice("科目C", Relevance.FOUNDATION, "理由C", "科目A"),
        ]
    )
    recommend = RecommendCourses(
        search, repository, FakeOccupationAnalyzer({"職業": PROFILE}), selector, 30
    )
    plans = FakePlanRepository()

    plan = CreatePlan(recommend, repository, plans, 2).run(
        OWNER, "職業", "情", 2026, START, {"科目A": "6T"}
    )

    [(_, candidates)] = selector.calls
    assert [candidate.name for candidate in candidates] == ["科目A", "科目B", "科目C"]
    assert plan.conditions == PlanConditions("職業", "情", 2026, START, (("科目A", "6T"),), 2)
    placed = [
        (semester_plan.semester, placed.course.name)
        for semester_plan in plan.roadmap.semesters
        for placed in semester_plan.courses
    ]
    assert len(plan.roadmap.semesters) == 4
    assert placed == [(START, "科目A"), (Semester(4, Term.SPRING), "科目B")]
    assert [course.name for course in plan.roadmap.unplaced] == ["科目C"]
    assert plans.plans == {plan.id: plan}
    assert plan.owner_id == OWNER


def test_courses_of_the_start_grade_that_only_open_before_the_start_term_are_not_candidates() -> (
    None
):
    repository, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    third_grade_only = (Audience(2020, 2026, frozenset({3}), "専門"),)
    a, b = repository.stored_sections
    repository.stored_sections = [replace(a, audiences=third_grade_only), b]
    selector = FakeCourseSelector([CourseChoice("科目B", Relevance.CORE, "理由B")])
    recommend = RecommendCourses(
        search, repository, FakeOccupationAnalyzer({"職業": PROFILE}), selector, 30
    )

    plan = CreatePlan(recommend, repository, FakePlanRepository(), 16).run(
        OWNER, "職業", "情", 2026, Semester(3, Term.AUTUMN), {}
    )

    [(_, candidates)] = selector.calls
    assert [candidate.name for candidate in candidates] == ["科目B"]
    assert plan.roadmap.semesters[0].semester == Semester(3, Term.AUTUMN)


def test_a_class_that_cannot_be_chosen_stops_before_the_llm_is_called() -> None:
    repository, search = courses_ranked_by({"情報科学Ⅱ": 0.9, "科目B": 0.8})
    a, b = repository.stored_sections
    own = frozenset({"情"})
    repository.stored_sections = [
        replace(a, class_code="TA", departments=own),
        replace(
            a, code="10002", class_code="TB", departments=own, slots=(TimeSlot(Weekday.TUE, 1),)
        ),
        b,
    ]
    analyzer = FakeOccupationAnalyzer({"職業": PROFILE})
    selector = FakeCourseSelector([])
    recommend = RecommendCourses(search, repository, analyzer, selector, 30)

    with pytest.raises(RoadmapError, match="情報科学Ⅱ: 選べるクラスは TA、TB です"):
        CreatePlan(recommend, repository, FakePlanRepository(), 16).run(
            OWNER, "職業", "情", 2026, START, {"情報科学Ⅱ": "TZ"}
        )
    assert (analyzer.calls, selector.calls) == ([], [])
