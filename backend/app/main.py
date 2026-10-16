from app.application.create_plan import CreatePlan
from app.application.get_plan import GetPlan
from app.application.identify_user import IdentifyUser
from app.infrastructure.auth.jwt_verifier import JwtVerifier
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.db.plans import SqlPlanRepository
from app.infrastructure.db.users import SqlUserRepository
from app.presentation.api.app import create_app
from app.presentation.composition import (
    auth_jwt_secret,
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
    get_plan=GetPlan(plans),
    identify=IdentifyUser(JwtVerifier(auth_jwt_secret(settings)), SqlUserRepository(engine)),
    curriculum_year=settings.curriculum_year,
    today=university_today,
)
