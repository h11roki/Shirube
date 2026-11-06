from dataclasses import replace

from app.domain.course import Audience, Term
from tests.fakes import FakeUserRepository, courses_ranked_by, plan_api


def test_courses_offered_in_the_remaining_semesters_are_listed_by_name() -> None:
    courses, search = courses_ranked_by({"科目B": 0.9, "科目A": 0.8, "科目C": 0.7, "科目D": 0.6})
    b, a, c, d = courses.stored_sections
    courses.stored_sections = [
        b,
        replace(b, code="10004", term=Term.AUTUMN, class_code="6U"),
        a,
        replace(c, audiences=(Audience(2020, 2026, frozenset({1}), "専門"),)),
        replace(d, departments=frozenset({"電"})),
    ]
    users = FakeUserRepository()
    users.add_taken(users.id_of("google-a"), "科目A")

    response = plan_api((courses, search), users=users).get(
        "/api/v1/offered-courses", params={"department": "情", "grade": 4, "term": "spring"}
    )

    assert (response.status_code, response.json()) == (
        200,
        {
            "term": "spring",
            "courses": [
                {
                    "name": "科目B",
                    "credits": 2,
                    "semesters": [{"grade": 4, "term": "spring"}, {"grade": 4, "term": "autumn"}],
                }
            ],
        },
    )


def test_the_start_term_defaults_to_spring_and_a_query_of_the_wrong_shape_is_unprocessable() -> (
    None
):
    api = plan_api()

    spring = api.get("/api/v1/offered-courses", params={"department": "情", "grade": 3})
    assert spring.status_code == 200
    assert spring.json()["term"] == "spring"
    wrong: list[dict[str, str | int]] = [
        {"department": "情", "grade": 5},
        {"department": " ", "grade": 3},
        {"grade": 3},
        {"department": "情", "grade": 3, "term": "summer"},
    ]
    for params in wrong:
        response = api.get("/api/v1/offered-courses", params=params)
        assert response.status_code == 422
        assert response.json()["detail"].startswith("リクエストを確かめてください: ")


def test_offered_courses_need_a_login() -> None:
    response = plan_api(token=None).get(
        "/api/v1/offered-courses", params={"department": "情", "grade": 3}
    )

    assert response.status_code == 401
