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

settings = load_settings()
engine = database_engine(settings)
plans = SqlPlanRepository(engine)
app = create_app(
    create_plan=CreatePlan(
        recommend=recommend_courses(settings, engine),
        courses=SqlCourseRepository(engine),
        plans=plans,
        credit_limit=settings.semester_credit_limit,
    ),
    plans=plans,
    curriculum_year=settings.curriculum_year,
    today=university_today,
)
