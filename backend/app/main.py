from fastapi import FastAPI

from app.application.create_plan import CreatePlan
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.db.plans import SqlPlanRepository
from app.presentation.api.app import create_app
from app.presentation.composition import (
    database_engine,
    load_settings,
    recommend_courses,
    university_today,
)


def build() -> FastAPI:
    settings = load_settings()
    engine = database_engine(settings)
    plans = SqlPlanRepository(engine)
    create_plan = CreatePlan(
        recommend_courses(settings, engine),
        SqlCourseRepository(engine),
        plans,
        settings.semester_credit_limit,
    )
    return create_app(create_plan, plans, settings.curriculum_year, university_today)


app = build()
