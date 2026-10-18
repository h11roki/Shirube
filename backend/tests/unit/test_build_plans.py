import logging
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from app.application.build_plans import (
    SERVER_FAILURE,
    STALLED,
    UPSTREAM_FAILURE,
    BuildPlans,
)
from app.application.recommend_courses import RecommendCourses
from app.application.search_courses import SearchCourses
from app.domain.course import Audience, Term, TimeSlot, Weekday
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan, PlanConditions, PlanStatus
from app.domain.recommendation import CourseChoice, Relevance
from app.domain.roadmap import Semester
from tests.fakes import (
    FakeChunkSearch,
    FakeCourseRepository,
    FakeCourseSelector,
    FakeEmbedder,
    FakeOccupationAnalyzer,
    FakePlanRepository,
    courses_ranked_by,
)

PROFILE = OccupationProfile("職業", "解釈した職業", None, ("甲", "乙", "丙"))
START = Semester(3, Term.SPRING)
OWNER = UUID("6f1c2a9e-3b4d-4e5f-8a7b-9c0d1e2f3a4b")


def waiting(
    plans: FakePlanRepository, start: Semester = START, chosen: tuple[tuple[str, str], ...] = ()
) -> Plan:
    plan = Plan(uuid4(), OWNER, PlanConditions("職業", "情", 2026, start, chosen, 2))
    plans.add(plan)
    return plan


def builder(
    courses_and_search: tuple[FakeCourseRepository, SearchCourses],
    plans: FakePlanRepository,
    selector: FakeCourseSelector | None = None,
    profile: OccupationProfile = PROFILE,
) -> BuildPlans:
    courses, search = courses_and_search
    recommend = RecommendCourses(
        search,
        courses,
        FakeOccupationAnalyzer({"職業": profile}),
        selector or FakeCourseSelector([]),
        30,
    )
    return BuildPlans(recommend, courses, plans)


def test_the_oldest_waiting_plan_is_recommended_placed_and_saved_as_succeeded() -> None:
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
    plans = FakePlanRepository()
    oldest = waiting(plans, chosen=(("科目A", "6T"),))
    newer = waiting(plans)

    built = builder((repository, search), plans, selector).build_next()

    assert built is not None
    assert built.id == oldest.id
    assert built.status is PlanStatus.SUCCEEDED
    assert built.result is not None
    [(_, candidates)] = selector.calls
    assert [candidate.name for candidate in candidates] == ["科目A", "科目B", "科目C"]
    placed = [
        (semester_plan.semester, placed.course.name)
        for semester_plan in built.result.roadmap.semesters
        for placed in semester_plan.courses
    ]
    assert placed == [(START, "科目A"), (Semester(4, Term.SPRING), "科目B")]
    assert [course.name for course in built.result.roadmap.unplaced] == ["科目C"]
    assert plans.plans[oldest.id] == built
    assert plans.plans[newer.id].status is PlanStatus.PENDING


def test_nothing_is_built_when_no_plan_is_waiting() -> None:
    plans = FakePlanRepository()

    assert builder(courses_ranked_by({"科目A": 0.9}), plans).build_next() is None


def test_courses_of_the_start_grade_that_only_open_before_the_start_term_are_not_candidates() -> (
    None
):
    repository, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    third_grade_only = (Audience(2020, 2026, frozenset({3}), "専門"),)
    a, b = repository.stored_sections
    repository.stored_sections = [replace(a, audiences=third_grade_only), b]
    selector = FakeCourseSelector([CourseChoice("科目B", Relevance.CORE, "理由B")])
    plans = FakePlanRepository()
    plan = waiting(plans, Semester(3, Term.AUTUMN))

    built = builder((repository, search), plans, selector).build(plan.id)

    [(_, candidates)] = selector.calls
    assert [candidate.name for candidate in candidates] == ["科目B"]
    assert built is not None
    assert built.result is not None
    assert built.result.roadmap.semesters[0].semester == Semester(3, Term.AUTUMN)


def test_only_a_waiting_plan_is_built_by_its_id() -> None:
    plans = FakePlanRepository()
    running = waiting(plans)
    plans.claim(running.id)
    failed = waiting(plans)
    plans.claim(failed.id)
    plans.finish(plans.plans[failed.id].failed("文"))
    selector = FakeCourseSelector([])
    build = builder(courses_ranked_by({"科目A": 0.9}), plans, selector)

    assert build.build(uuid4()) is None
    assert build.build(running.id) is None
    assert build.build(failed.id) is None
    assert selector.calls == []


def test_a_failed_external_call_fails_the_plan_with_a_fixed_message_and_logs_the_cause(
    caplog: pytest.LogCaptureFixture,
) -> None:
    repository, _ = courses_ranked_by({"科目A": 0.9})
    hits = FakeChunkSearch([])
    search = SearchCourses(repository, hits, FakeEmbedder(failing_call=1))
    plans = FakePlanRepository()
    plan = waiting(plans)

    with caplog.at_level(logging.ERROR):
        built = builder((repository, search), plans).build_next()

    assert built is not None
    assert (built.status, built.failure) == (PlanStatus.FAILED, UPSTREAM_FAILURE)
    assert plans.plans[plan.id] == built
    assert "埋め込みの API 呼び出しに失敗しました" in caplog.text


def test_an_unexpected_error_fails_the_plan_with_the_server_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    other = OccupationProfile("別の職業", "別の職業", None, ("甲", "乙", "丙"))
    plans = FakePlanRepository()
    plan = waiting(plans)

    with caplog.at_level(logging.ERROR):
        built = builder(courses_ranked_by({"科目A": 0.9}), plans, profile=other).build_next()

    assert built is not None
    assert (built.status, built.failure) == (PlanStatus.FAILED, SERVER_FAILURE)
    assert plans.plans[plan.id] == built
    assert "推薦の職業が条件と違います: 別の職業" in caplog.text


def test_a_plan_that_stopped_running_while_it_was_built_keeps_its_stored_state(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class StalledWhileBuilding(FakePlanRepository):
        def finish(self, plan: Plan) -> bool:
            self.fail_stalled(timedelta(minutes=15), STALLED)
            return super().finish(plan)

    plans = StalledWhileBuilding()
    plan = waiting(plans)

    with caplog.at_level(logging.WARNING):
        built = builder(courses_ranked_by({"科目A": 0.9}), plans).build_next()

    assert built is not None
    assert (built.status, built.failure) == (PlanStatus.FAILED, STALLED)
    assert plans.plans[plan.id] == built
    assert "作成中でなくなったので、結果を捨てました" in caplog.text


def test_plans_running_past_the_limit_fail_as_stalled(caplog: pytest.LogCaptureFixture) -> None:
    plans = FakePlanRepository()
    stuck = waiting(plans)
    plans.claim(stuck.id)
    untouched = waiting(plans)

    with caplog.at_level(logging.WARNING):
        stalled = builder(courses_ranked_by({"科目A": 0.9}), plans).fail_stalled(
            timedelta(minutes=15)
        )

    assert stalled == [stuck.id]
    assert plans.stall_limits == [timedelta(minutes=15)]
    assert (plans.plans[stuck.id].status, plans.plans[stuck.id].failure) == (
        PlanStatus.FAILED,
        STALLED,
    )
    assert plans.plans[untouched.id].status is PlanStatus.PENDING
    assert str(stuck.id) in caplog.text
