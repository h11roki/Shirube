from fastapi import FastAPI

from app.presentation.api import health

app = FastAPI(title="shirube")
app.include_router(health.router, prefix="/api/v1")
