from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.application.build_plans import SERVER_FAILURE
from app.application.ports import PlanFormatError
from app.application.search_courses import SearchCourses
from app.domain.course import TimeSlot, Weekday
from app.domain.plan import Plan, PlanStage, PlanStatus
from tests.builders import sample_conditions, sample_plan, sample_plan_asking
from tests.fakes import (
    FakeChunkSearch,
    FakeCourseRepository,
    FakeEmbedder,
    FakePlanRepository,
    FakeUserRepository,
    courses_ranked_by,
    plan_api,
)


class UnreadablePlans(FakePlanRepository):
    def get_owned_by(self, plan_id: UUID, owner_id: UUID) -> Plan | None:
        raise PlanFormatError(f"{plan_id}: 読めない版の道標の結果です: 3")


class BrokenPlans(FakePlanRepository):
    def add(self, plan: Plan) -> None:
        raise RuntimeError("接続文字列 postgresql://secret")


def client(
    courses_and_search: tuple[FakeCourseRepository, SearchCourses] | None = None,
    plans: FakePlanRepository | None = None,
    users: FakeUserRepository | None = None,
    token: str | None = "token-a",
) -> TestClient:
    return plan_api(courses_and_search, plans, users, token)


def body(**fields: Any) -> dict[str, Any]:
    return {"occupation": "職業", "grade": 3, "department": "情", **fields}


def test_a_requested_plan_is_saved_waiting_for_the_user_and_accepted_with_its_location() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()

    response = client(plans=plans, users=users).post("/api/v1/plans", json=body())

    assert response.status_code == 202
    [plan_id] = plans.plans
    assert plans.plans[plan_id].owner_id == users.users["google-a"]
    assert response.headers["location"] == f"/api/v1/plans/{plan_id}"
    assert response.json() == {
        "id": str(plan_id),
        "status": "pending",
        "stage": None,
        "conditions": {
            "occupation": "職業",
            "department": "情",
            "year": 2026,
            "grade": 3,
            "term": "autumn",
            "chosen_classes": {},
            "credit_limit": 16,
        },
        "result": None,
        "failure": None,
    }


def test_a_given_term_overrides_the_term_of_today() -> None:
    response = client().post("/api/v1/plans", json=body(term="spring"))

    assert response.json()["conditions"]["term"] == "spring"


def test_a_waiting_plan_is_shown_as_it_was_accepted() -> None:
    api = client()
    accepted = api.post("/api/v1/plans", json=body()).json()

    response = api.get(f"/api/v1/plans/{accepted['id']}")

    assert (response.status_code, response.json()) == (200, accepted)


def test_a_running_plan_is_shown_with_its_stage() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    plan = Plan(
        uuid4(),
        users.id_of("google-a"),
        sample_conditions(),
        PlanStatus.RUNNING,
        stage=PlanStage.SELECTING,
    )
    plans.add(plan)

    shown = client(plans=plans, users=users).get(f"/api/v1/plans/{plan.id}").json()

    assert (shown["status"], shown["stage"]) == ("running", "selecting")


def test_a_succeeded_plan_is_shown_with_its_result() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    plan = sample_plan(uuid4(), users.id_of("google-a"))
    plans.add(plan)

    shown = client(plans=plans, users=users).get(f"/api/v1/plans/{plan.id}").json()

    assert (shown["status"], shown["failure"]) == ("succeeded", None)
    result = shown["result"]
    assert result["profile"]["interpretation"] == "解釈した職業"
    assert [(semester["grade"], semester["term"]) for semester in result["semesters"]] == [
        (3, "spring"),
        (3, "autumn"),
        (4, "spring"),
        (4, "autumn"),
    ]
    assert result["semesters"][0]["courses"][0] == {
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
    assert [course["name"] for course in result["semesters"][1]["continuing"]] == ["科目B"]
    assert [course["name"] for course in result["unplaced"]] == ["科目D"]
    assert (result["taken"], result["offered_earlier"]) == ([], [])
    assert result["unlinked"] == [{"name": "科目E", "reason": "理由E", "prerequisite_for": "科目F"}]


def test_a_failed_plan_is_shown_with_its_fixed_message() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    plan = Plan(
        uuid4(),
        users.id_of("google-a"),
        sample_conditions(),
        PlanStatus.FAILED,
        failure="道標を作る途中で止まりました",
    )
    plans.add(plan)

    shown = client(plans=plans, users=users).get(f"/api/v1/plans/{plan.id}").json()

    assert (shown["status"], shown["result"], shown["failure"]) == (
        "failed",
        None,
        "道標を作る途中で止まりました",
    )


def test_the_list_shows_only_the_users_own_plans_newest_first_up_to_fifty() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    owner = users.id_of("google-a")
    own = [Plan(uuid4(), owner, sample_conditions()) for _ in range(51)]
    for plan in own:
        plans.add(plan)
    plans.add(Plan(uuid4(), users.id_of("google-b"), sample_conditions()))

    listed = client(plans=plans, users=users).get("/api/v1/plans")

    assert listed.status_code == 200
    summaries = listed.json()["plans"]
    assert [summary["id"] for summary in summaries] == [str(plan.id) for plan in own[:0:-1]]
    assert summaries[0] == {
        "id": str(own[-1].id),
        "status": "pending",
        "occupation": "職業",
        "grade": 3,
        "term": "spring",
        "created_at": plans.created_at[own[-1].id].isoformat().replace("+00:00", "Z"),
    }


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


def test_problems_on_the_server_are_server_errors_without_their_details() -> None:
    courses, _ = courses_ranked_by({"科目A": 0.9})
    not_embedded = SearchCourses(courses, FakeChunkSearch([], embedded=False), FakeEmbedder())
    empty = FakeCourseRepository()
    no_data = SearchCourses(empty, FakeChunkSearch([]), FakeEmbedder())

    for api in (
        client((courses, not_embedded)),
        client((empty, no_data)),
        client(plans=BrokenPlans()),
    ):
        response = api.post("/api/v1/plans", json=body())
        assert (response.status_code, response.json()) == (500, {"detail": SERVER_FAILURE})


def test_a_stored_plan_that_cannot_be_read_is_a_server_error() -> None:
    response = client(plans=UnreadablePlans()).get(f"/api/v1/plans/{uuid4()}")

    assert (response.status_code, response.json()) == (500, {"detail": SERVER_FAILURE})


def test_plans_need_a_login() -> None:
    api = client(token=None)

    for response in (
        api.post("/api/v1/plans", json=body()),
        api.get(f"/api/v1/plans/{uuid4()}"),
        api.get("/api/v1/plans"),
        api.get("/api/v1/class-choices", params={"department": "情", "grade": 3}),
    ):
        assert (response.status_code, response.json()) == (401, {"detail": "ログインしてください"})
        assert response.headers["www-authenticate"] == "Bearer"


def test_a_token_that_cannot_be_verified_is_unauthorized_without_its_reason() -> None:
    response = client(token="token-z").post("/api/v1/plans", json=body())

    assert (response.status_code, response.json()) == (401, {"detail": "ログインしてください"})
    assert response.headers["www-authenticate"] == 'Bearer error="invalid_token"'


def test_another_users_plan_is_not_found() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    accepted = client(plans=plans, users=users).post("/api/v1/plans", json=body()).json()

    response = client(plans=plans, users=users, token="token-b").get(
        f"/api/v1/plans/{accepted['id']}"
    )

    assert (response.status_code, response.json()) == (
        404,
        {"detail": f"Plan がありません: {accepted['id']}"},
    )


def test_answering_taken_courses_returns_the_plan_placed_again() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    plan = sample_plan_asking(uuid4(), users.id_of("google-a"))
    plans.add(plan)
    courses = courses_ranked_by({"科目A": 0.9, "科目B": 0.8, "科目C": 0.7, "科目D": 0.6})

    response = client(courses, plans, users).put(
        f"/api/v1/plans/{plan.id}/taken-courses", json={"names": ["科目A"]}
    )

    assert response.status_code == 200
    result = response.json()["result"]
    assert [course["name"] for course in result["taken"]] == ["科目A"]
    assert result["offered_earlier"] == ["科目A", "科目B", "科目C", "科目D"]


def test_answering_about_a_course_not_asked_or_on_an_unfinished_plan_is_refused() -> None:
    plans = FakePlanRepository()
    users = FakeUserRepository()
    owner = users.id_of("google-a")
    plan = sample_plan_asking(uuid4(), owner)
    waiting = Plan(uuid4(), owner, sample_conditions())
    plans.add(plan)
    plans.add(waiting)
    api = client(plans=plans, users=users)

    unasked = api.put(f"/api/v1/plans/{plan.id}/taken-courses", json={"names": ["科目B"]})
    unfinished = api.put(f"/api/v1/plans/{waiting.id}/taken-courses", json={"names": []})
    others = client(plans=plans, users=users, token="token-b").put(
        f"/api/v1/plans/{plan.id}/taken-courses", json={"names": ["科目A"]}
    )
    wrong_shape = api.put(f"/api/v1/plans/{plan.id}/taken-courses", json={"name": "科目A"})

    assert (unasked.status_code, unasked.json()) == (
        422,
        {"detail": "この道標でもう取ったかを聞いていない授業です: 科目B"},
    )
    assert unfinished.status_code == 409
    assert unfinished.json()["detail"].startswith("できあがっていない道標では答えられません")
    assert others.status_code == 404
    assert wrong_shape.status_code == 422
