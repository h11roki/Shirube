from datetime import date

from fastapi.testclient import TestClient

from app.application.create_plan import CreatePlan
from app.application.recommend_courses import RecommendCourses
from app.presentation.api.app import create_app
from tests.fakes import (
    FakeCourseSelector,
    FakeOccupationAnalyzer,
    FakePlanRepository,
    courses_ranked_by,
)


def test_health_returns_ok() -> None:
    repository, search = courses_ranked_by({"科目A": 0.9})
    recommend = RecommendCourses(
        search, repository, FakeOccupationAnalyzer({}), FakeCourseSelector([]), 30
    )
    plans = FakePlanRepository()
    app = create_app(CreatePlan(recommend, repository, plans, 16), plans, 2026, date.today)

    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
