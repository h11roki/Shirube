from dataclasses import replace
from datetime import date
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.application.ports import CourseSelectionError, PlanFormatError
from app.application.search_courses import SearchCourses
from app.domain.course import TimeSlot, Weekday
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan
from app.domain.recommendation import CandidateCourse, CourseChoice, Relevance
from tests.fakes import (
    FakeChunkSearch,
    FakeCourseRepository,
    FakeCourseSelector,
    FakeEmbedder,
    FakePlanRepository,
    courses_ranked_by,
    plan_api,
)

PROFILE = OccupationProfile("職業", "解釈した職業", None, ("甲", "乙", "丙"))
TODAY = date(2026, 10, 16)
CHOICES = [
    CourseChoice("科目A", Relevance.CORE, "理由A"),
    CourseChoice("科目B", Relevance.FOUNDATION, "理由B", "科目A"),
]


class FailingSelector:
    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        raise CourseSelectionError(f"{profile.occupation}: LLM の答えを使えません")


class UnreadablePlans(FakePlanRepository):
    def get(self, plan_id: UUID) -> Plan | None:
        raise PlanFormatError(f"{plan_id}: 読めない版の Plan です: 2")


class BrokenPlans(FakePlanRepository):
    def add(self, plan: Plan) -> None:
        raise RuntimeError("接続文字列 postgresql://secret")


def client(
    repository: FakeCourseRepository | None = None,
    selector: FakeCourseSelector | FailingSelector | None = None,
    plans: FakePlanRepository | None = None,
) -> TestClient:
    ranked, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    courses = repository or ranked
    return plan_api((courses, search), selector or FakeCourseSelector(CHOICES), plans)


def body(**fields: Any) -> dict[str, Any]:
    return {"occupation": "職業", "grade": 3, "department": "情", **fields}


def test_creating_a_plan_saves_it_and_returns_it_with_its_location() -> None:
    plans = FakePlanRepository()

    response = client(plans=plans).post("/api/v1/plans", json=body())

    assert response.status_code == 201
    created = response.json()
    [plan_id] = plans.plans
    assert created["id"] == str(plan_id)
    assert response.headers["location"] == f"/api/v1/plans/{plan_id}"
    assert created["conditions"] == {
        "occupation": "職業",
        "department": "情",
        "year": 2026,
        "grade": 3,
        "term": "autumn",
        "chosen_classes": {},
        "credit_limit": 16,
    }
    assert created["profile"]["interpretation"] == "解釈した職業"
    assert [(semester["grade"], semester["term"]) for semester in created["semesters"]] == [
        (3, "autumn"),
        (4, "spring"),
        (4, "autumn"),
    ]
    assert created["semesters"][1]["courses"] == [
        {
            "name": "科目A",
            "relevance": "core",
            "reason": "理由A",
            "prerequisite_for": None,
            "syllabus_code": "10000",
            "section_code": "10000",
            "class_code": "6T",
            "slots": [{"weekday": "mon", "period": 1}, {"weekday": "mon", "period": 2}],
            "credits": 2,
            "class_confirmed": True,
        }
    ]
    assert [course["name"] for course in created["unplaced"]] == ["科目B"]
    assert created["unlinked"] == []


def test_a_given_term_overrides_the_term_of_today() -> None:
    response = client().post("/api/v1/plans", json=body(term="spring"))

    first = response.json()["semesters"][0]
    assert response.json()["conditions"]["term"] == "spring"
    assert (first["grade"], first["term"]) == (3, "spring")


def test_a_saved_plan_is_shown_as_it_was_created() -> None:
    api = client()
    created = api.post("/api/v1/plans", json=body()).json()

    response = api.get(f"/api/v1/plans/{created['id']}")

    assert (response.status_code, response.json()) == (200, created)


def test_an_unknown_plan_is_not_found() -> None:
    plan_id = uuid4()

    response = client().get(f"/api/v1/plans/{plan_id}")

    assert (response.status_code, response.json()) == (
        404,
        {"detail": f"Plan がありません: {plan_id}"},
    )


def test_a_body_of_the_wrong_shape_is_unprocessable() -> None:
    api = client()

    for wrong in (
        body(grade=5),
        body(occupation="職業\n別の行"),
        body(term="summer"),
        {"occupation": "職業", "grade": 3},
    ):
        assert api.post("/api/v1/plans", json=wrong).status_code == 422


def test_a_class_that_cannot_be_chosen_is_unprocessable() -> None:
    repository, _ = courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    a, b = repository.stored_sections
    own = frozenset({"情"})
    repository.stored_sections = [
        replace(a, class_code="TA", departments=own),
        replace(
            a, code="10002", class_code="TB", departments=own, slots=(TimeSlot(Weekday.TUE, 1),)
        ),
        b,
    ]

    response = client(repository=repository).post(
        "/api/v1/plans", json=body(chosen_classes={"科目A": "TZ"})
    )

    assert (response.status_code, response.json()) == (
        422,
        {"detail": "科目A: 選べるクラスは TA、TB です"},
    )


def test_a_department_without_candidates_is_unprocessable() -> None:
    response = client().post("/api/v1/plans", json=body(department="機"))

    assert response.status_code == 422
    assert "候補の科目がありません" in response.json()["detail"]


def test_an_unusable_llm_answer_is_a_bad_gateway() -> None:
    response = client(selector=FailingSelector()).post("/api/v1/plans", json=body())

    assert (response.status_code, response.json()) == (
        502,
        {"detail": "職業: LLM の答えを使えません"},
    )


def test_a_stored_plan_that_cannot_be_read_is_a_server_error() -> None:
    plan_id = uuid4()

    response = client(plans=UnreadablePlans()).get(f"/api/v1/plans/{plan_id}")

    assert (response.status_code, response.json()) == (
        500,
        {"detail": f"{plan_id}: 読めない版の Plan です: 2"},
    )


def test_search_problems_on_the_server_are_server_errors() -> None:
    courses, _ = courses_ranked_by({"科目A": 0.9})
    search = SearchCourses(courses, FakeChunkSearch([], embedded=False), FakeEmbedder())

    response = plan_api((courses, search)).post("/api/v1/plans", json=body())

    assert response.status_code == 500
    assert "埋め込まれていません" in response.json()["detail"]


def test_an_embedding_failure_is_a_bad_gateway() -> None:
    courses, _ = courses_ranked_by({"科目A": 0.9})
    search = SearchCourses(courses, FakeChunkSearch([]), FakeEmbedder(failing_call=1))

    response = plan_api((courses, search)).post("/api/v1/plans", json=body())

    assert response.status_code == 502
    assert "埋め込みの API 呼び出しに失敗しました" in response.json()["detail"]


def test_an_unexpected_failure_is_a_server_error_without_its_details() -> None:
    response = client(plans=BrokenPlans()).post("/api/v1/plans", json=body())

    assert (response.status_code, response.json()) == (
        500,
        {"detail": "サーバーで道標を扱えませんでした"},
    )
