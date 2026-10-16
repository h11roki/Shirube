from tests.fakes import plan_api


def test_health_returns_ok_without_a_login() -> None:
    response = plan_api(token=None).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
