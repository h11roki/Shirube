from tests.fakes import plan_api


def test_health_returns_ok() -> None:
    response = plan_api().get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
