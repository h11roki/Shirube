from dataclasses import replace
from datetime import date

from app.domain.course import Audience, TimeSlot, Weekday
from tests.fakes import FakeUserRepository, courses_ranked_by, plan_api

OWN = frozenset({"情"})


def test_courses_split_into_department_classes_in_the_remaining_semesters_are_listed() -> None:
    courses, search = courses_ranked_by({"情報科学Ⅱ": 0.9, "科目B": 0.8})
    split, other = courses.stored_sections
    courses.stored_sections = [
        replace(split, class_code="TA", departments=OWN),
        replace(
            split, code="10002", class_code="TB", departments=OWN, slots=(TimeSlot(Weekday.TUE, 1),)
        ),
        other,
    ]

    api = plan_api((courses, search))

    response = api.get(
        "/api/v1/class-choices", params={"department": "情", "grade": 3, "term": "spring"}
    )
    padded = api.get(
        "/api/v1/class-choices", params={"department": " 情 ", "grade": 3, "term": "spring"}
    )

    assert (response.status_code, response.json()) == (
        200,
        {"term": "spring", "courses": [{"name": "情報科学Ⅱ", "class_codes": ["TA", "TB"]}]},
    )
    assert padded.json() == response.json()


def test_the_start_term_defaults_to_today_and_limits_the_semesters() -> None:
    courses, search = courses_ranked_by({"情報科学Ⅱ": 0.9})
    [split] = courses.stored_sections
    third_grade_spring = (Audience(2020, 2026, frozenset({3}), "専門"),)
    courses.stored_sections = [
        replace(split, class_code="TA", departments=OWN, audiences=third_grade_spring),
        replace(
            split,
            code="10002",
            class_code="TB",
            departments=OWN,
            audiences=third_grade_spring,
            slots=(TimeSlot(Weekday.TUE, 1),),
        ),
    ]
    in_autumn = plan_api((courses, search), today=date(2026, 10, 19))
    in_spring = plan_api((courses, search), today=date(2026, 4, 10))

    params: dict[str, str | int] = {"department": "情", "grade": 3}
    assert in_autumn.get("/api/v1/class-choices", params=params).json() == {
        "term": "autumn",
        "courses": [],
    }
    assert in_spring.get("/api/v1/class-choices", params=params).json() == {
        "term": "spring",
        "courses": [{"name": "情報科学Ⅱ", "class_codes": ["TA", "TB"]}],
    }


def test_a_query_of_the_wrong_shape_is_unprocessable() -> None:
    api = plan_api()

    wrong: list[dict[str, str | int]] = [
        {"department": "情", "grade": 5},
        {"department": "", "grade": 3},
        {"department": "  ", "grade": 3},
        {"grade": 3},
        {"department": "情", "grade": 3, "term": "summer"},
    ]
    for params in wrong:
        response = api.get("/api/v1/class-choices", params=params)
        assert response.status_code == 422
        assert response.json()["detail"].startswith("リクエストを確かめてください: ")


def test_courses_the_user_has_taken_are_not_offered_as_choices() -> None:
    courses, search = courses_ranked_by({"情報科学Ⅱ": 0.9, "科目B": 0.8})
    split, other = courses.stored_sections
    courses.stored_sections = [
        replace(split, class_code="TA", departments=OWN),
        replace(
            split, code="10002", class_code="TB", departments=OWN, slots=(TimeSlot(Weekday.TUE, 1),)
        ),
        other,
    ]
    users = FakeUserRepository()
    users.add_taken(users.id_of("google-a"), "情報科学Ⅱ")

    response = plan_api((courses, search), users=users).get(
        "/api/v1/class-choices", params={"department": "情", "grade": 3, "term": "spring"}
    )

    assert response.json() == {"term": "spring", "courses": []}
