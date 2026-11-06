from fastapi import APIRouter, Response, status

from app.application.check_health import CheckHealth
from app.presentation.schemas.health import HealthOut


def health_router(check_health: CheckHealth, version: str) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/health",
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthOut}},
    )
    def health(response: Response) -> HealthOut:
        found = check_health.run()
        if not found.database_reachable:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return HealthOut(
                status="down", version=version, database="down", queue="unknown", openai="unknown"
            )
        return HealthOut(
            status="degraded" if found.queue_stalled or found.out_of_credit else "ok",
            version=version,
            database="ok",
            queue="stalled" if found.queue_stalled else "ok",
            openai="out_of_credit" if found.out_of_credit else "ok",
        )

    return router
