from dataclasses import replace
from uuid import UUID

import pytest

from app.application.request_plan import RequestPlan
from app.application.search_courses import NoCandidatesError
from app.domain.course import Term, TimeSlot, Weekday
from app.domain.plan import PlanConditions, PlanStatus
from app.domain.roadmap import RoadmapError, Semester
from tests.fakes import FakePlanRepository, courses_ranked_by

START = Semester(3, Term.SPRING)
OWNER = UUID("6f1c2a9e-3b4d-4e5f-8a7b-9c0d1e2f3a4b")


def test_a_request_is_saved_waiting_with_its_conditions() -> None:
    repository, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    plans = FakePlanRepository()

    plan = RequestPlan(search, repository, plans, 16).run(
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
        RequestPlan(search, repository, plans, 16).run(
            OWNER, "職業", "情", 2026, START, {"情報科学Ⅱ": "TZ"}
        )
    assert plans.plans == {}


def test_a_department_without_candidates_is_refused_without_saving() -> None:
    repository, search = courses_ranked_by({"科目A": 0.9})
    plans = FakePlanRepository()

    with pytest.raises(NoCandidatesError, match="2026 年度の 機 に"):
        RequestPlan(search, repository, plans, 16).run(OWNER, "職業", "機", 2026, START, {})
    assert plans.plans == {}
