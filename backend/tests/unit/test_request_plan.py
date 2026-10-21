from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.application.request_plan import RequestPlan
from app.application.search_courses import NoCandidatesError
from app.domain.course import Term, TimeSlot, Weekday
from app.domain.plan import Plan, PlanConditions, PlanStage, PlanStatus
from app.domain.quota import DailyLimitError, PlanInProgressError, PlanQuota
from app.domain.roadmap import RoadmapError, Semester
from tests.builders import sample_conditions, sample_plan
from tests.fakes import (
    FIRST_CREATED_AT,
    QUOTA,
    FakePlanRepository,
    FakeUserRepository,
    courses_ranked_by,
)

START = Semester(3, Term.SPRING)
OWNER = UUID("6f1c2a9e-3b4d-4e5f-8a7b-9c0d1e2f3a4b")
OTHER = UUID("0b8f3c2d-1e4a-4b5c-9d6e-7f8a9b0c1d2e")
NOW = FIRST_CREATED_AT + timedelta(hours=1)


def test_a_request_is_saved_waiting_with_its_conditions() -> None:
    repository, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    plans = FakePlanRepository()

    plan = RequestPlan(search, repository, plans, FakeUserRepository(), 16, QUOTA, lambda: NOW).run(
        OWNER, "職業", "情", 2026, START, {"科目A": "6T"}
    )

    assert plan.status is PlanStatus.PENDING
    assert plan.owner_id == OWNER
    assert plan.conditions == PlanConditions("職業", "情", 2026, START, (("科目A", "6T"),), 16)
    assert plans.plans == {plan.id: plan}


def test_a_class_that_cannot_be_chosen_is_refused_without_saving() -> None:
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
    plans = FakePlanRepository()

    with pytest.raises(RoadmapError, match="情報科学Ⅱ: 選べるクラスは TA、TB です"):
        RequestPlan(search, repository, plans, FakeUserRepository(), 16, QUOTA, lambda: NOW).run(
            OWNER, "職業", "情", 2026, START, {"情報科学Ⅱ": "TZ"}
        )
    assert plans.plans == {}


def test_a_department_without_candidates_is_refused_without_saving() -> None:
    repository, search = courses_ranked_by({"科目A": 0.9})
    plans = FakePlanRepository()

    with pytest.raises(NoCandidatesError, match="2026 年度の 機 に"):
        RequestPlan(search, repository, plans, FakeUserRepository(), 16, QUOTA, lambda: NOW).run(
            OWNER, "職業", "機", 2026, START, {}
        )
    assert plans.plans == {}


def test_a_request_whose_candidates_are_all_taken_is_refused_without_saving() -> None:
    repository, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    plans = FakePlanRepository()
    users = FakeUserRepository()
    users.add_taken(OWNER, "科目A")
    users.add_taken(OWNER, "科目B")

    with pytest.raises(NoCandidatesError, match="もう取ったと答えた授業は除いています"):
        RequestPlan(search, repository, plans, users, 16, QUOTA, lambda: NOW).run(
            OWNER, "職業", "情", 2026, START, {}
        )

    assert plans.plans == {}


def request_with(plans: FakePlanRepository, quota: PlanQuota = QUOTA) -> Plan:
    repository, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    return RequestPlan(search, repository, plans, FakeUserRepository(), 16, quota, lambda: NOW).run(
        OWNER, "職業", "情", 2026, START, {}
    )


def waiting(owner_id: UUID) -> Plan:
    return Plan(uuid4(), owner_id, sample_conditions())


def failed(owner_id: UUID) -> Plan:
    return replace(waiting(owner_id), status=PlanStatus.RUNNING).failed("失敗")


@pytest.mark.parametrize(
    "unfinished",
    [waiting(OWNER), replace(waiting(OWNER), status=PlanStatus.RUNNING, stage=PlanStage.ANALYZING)],
    ids=["pending", "running"],
)
def test_a_user_with_a_plan_in_progress_is_refused_without_saving(unfinished: Plan) -> None:
    plans = FakePlanRepository()
    plans.store(unfinished)

    with pytest.raises(PlanInProgressError, match="作っている道標ができてから"):
        request_with(plans)
    assert list(plans.plans) == [unfinished.id]


def test_a_user_who_made_three_plans_today_is_refused_until_midnight_in_japan() -> None:
    plans = FakePlanRepository()
    for _ in range(3):
        plans.store(sample_plan(uuid4(), OWNER))

    with pytest.raises(DailyLimitError, match="1 人 1 日 3 件まで") as refused:
        request_with(plans)

    assert refused.value.retry_after == timedelta(hours=5)
    assert len(plans.plans) == 3


def test_the_users_failed_plans_and_plans_before_today_are_not_counted() -> None:
    plans = FakePlanRepository()
    for _ in range(3):
        plans.store(failed(OWNER))
    yesterday = sample_plan(uuid4(), OWNER)
    plans.store(yesterday)
    plans.created_at[yesterday.id] = datetime.fromisoformat("2026-10-18T23:59+09:00")

    assert request_with(plans).status is PlanStatus.PENDING


def test_all_plans_today_including_failed_ones_are_counted_against_the_total() -> None:
    plans = FakePlanRepository()
    plans.store(sample_plan(uuid4(), OTHER))
    plans.store(failed(OTHER))

    with pytest.raises(DailyLimitError, match="全体で作れる 2 件に達しました"):
        request_with(plans, PlanQuota(per_user=3, total=2))


def test_deleted_plans_still_count_against_the_day() -> None:
    plans = FakePlanRepository()
    for _ in range(3):
        plans.store(sample_plan(uuid4(), OWNER))
    plans.delete_owned_by(next(iter(plans.plans)), OWNER)

    with pytest.raises(DailyLimitError, match="1 人 1 日 3 件まで"):
        request_with(plans)
