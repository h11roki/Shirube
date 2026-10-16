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
from app.domain.roadmap import RoadmapError
from app.presentation.api.app import SERVER_FAILURE, UPSTREAM_FAILURE
from tests.fakes import (
    FakeChunkSearch,
    FakeCourseRepository,
    FakeCourseSelector,
    FakeEmbedder,
    FakePlanRepository,
    FakeUserRepository,
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
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self._error = error

    def add(self, plan: Plan) -> None:
        raise self._error


def client(
    courses_and_search: tuple[FakeCourseRepository, SearchCourses] | None = None,
    selector: FakeCourseSelector | FailingSelector | None = None,
    plans: FakePlanRepository | None = None,
    users: FakeUserRepository | None = None,
    token: str | None = "token-a",
) -> TestClient:
    return plan_api(
        courses_and_search or courses_ranked_by({"科目A": 0.9, "科目B": 0.8}),
        selector or FakeCourseSelector(CHOICES),
        plans,
        users,
        token,
    )


def body(**fields: Any) -> dict[str, Any]:
    return {"occupation": "職業", "grade": 3, "department": "情", **fields}


def test_creating_a_plan_saves_it_for_the_user_and_returns_it_with_its_location() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()

    response = client(plans=plans, users=users).post("/api/v1/plans", json=body())

    assert response.status_code == 201
    created = response.json()
    [plan_id] = plans.plans
    assert created["id"] == str(plan_id)
    assert plans.plans[plan_id].owner_id == users.users["google-a"]
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


def test_a_request_of_the_wrong_shape_is_unprocessable_with_one_message() -> None:
    api = client()

    for wrong in (
        body(grade=5),
        body(occupation="職業\n別の行"),
        body(term="summer"),
        body(chosenClasses={"科目A": "TA"}),
        body(grade=True),
        body(grade="3"),
        body(department="情" * 101),
        {"occupation": "職業", "grade": 3},
    ):
        response = api.post("/api/v1/plans", json=wrong)
        assert response.status_code == 422
        assert response.json()["detail"].startswith("リクエストを確かめてください: ")
    response = api.post("/api/v1/plans", content="{壊れた")
    assert response.json()["detail"].startswith("リクエストを確かめてください: 本文: ")
    response = api.get("/api/v1/plans/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["detail"].startswith("リクエストを確かめてください: plan_id: ")


def test_a_class_that_cannot_be_chosen_is_unprocessable() -> None:
    repository, search = courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    a, b = repository.stored_sections
    own = frozenset({"情"})
    repository.stored_sections = [
        replace(a, class_code="TA", departments=own),
        replace(
            a, code="10002", class_code="TB", departments=own, slots=(TimeSlot(Weekday.TUE, 1),)
        ),
        b,
    ]

    response = client((repository, search)).post(
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


def test_failures_of_outside_services_are_a_bad_gateway_without_their_details() -> None:
    courses, _ = courses_ranked_by({"科目A": 0.9})
    failing_embedding = SearchCourses(courses, FakeChunkSearch([]), FakeEmbedder(failing_call=1))

    for api in (client(selector=FailingSelector()), client((courses, failing_embedding))):
        response = api.post("/api/v1/plans", json=body())
        assert (response.status_code, response.json()) == (502, {"detail": UPSTREAM_FAILURE})


def test_problems_on_the_server_are_server_errors_without_their_details() -> None:
    courses, _ = courses_ranked_by({"科目A": 0.9})
    not_embedded = SearchCourses(courses, FakeChunkSearch([], embedded=False), FakeEmbedder())
    empty = FakeCourseRepository()
    no_data = SearchCourses(empty, FakeChunkSearch([]), FakeEmbedder())
    broken_roadmap = BrokenPlans(RoadmapError("3 回生 秋学期: 同じコマに 2 つの授業があります"))
    broken_connection = BrokenPlans(RuntimeError("接続文字列 postgresql://secret"))

    for api in (
        client((courses, not_embedded)),
        client((empty, no_data)),
        client(plans=broken_roadmap),
        client(plans=broken_connection),
    ):
        response = api.post("/api/v1/plans", json=body())
        assert (response.status_code, response.json()) == (500, {"detail": SERVER_FAILURE})


def test_a_stored_plan_that_cannot_be_read_is_a_server_error() -> None:
    response = client(plans=UnreadablePlans()).get(f"/api/v1/plans/{uuid4()}")

    assert (response.status_code, response.json()) == (500, {"detail": SERVER_FAILURE})


def test_plans_need_a_login() -> None:
    api = client(token=None)

    for response in (api.post("/api/v1/plans", json=body()), api.get(f"/api/v1/plans/{uuid4()}")):
        assert (response.status_code, response.json()) == (401, {"detail": "ログインしてください"})
        assert response.headers["www-authenticate"] == "Bearer"


def test_a_token_that_cannot_be_verified_is_unauthorized_without_its_reason() -> None:
    response = client(token="token-z").post("/api/v1/plans", json=body())

    assert (response.status_code, response.json()) == (401, {"detail": "ログインしてください"})
    assert response.headers["www-authenticate"] == "Bearer"


def test_another_users_plan_is_not_found() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    created = client(plans=plans, users=users).post("/api/v1/plans", json=body()).json()

    response = client(plans=plans, users=users, token="token-b").get(
        f"/api/v1/plans/{created['id']}"
    )

    assert (response.status_code, response.json()) == (
        404,
        {"detail": f"Plan がありません: {created['id']}"},
    )
