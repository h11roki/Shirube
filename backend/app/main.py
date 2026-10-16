import sys

from app.application.create_plan import CreatePlan
from app.application.get_plan import GetPlan
from app.application.identify_user import IdentifyUser
from app.infrastructure.auth.jwt_verifier import JwtVerifier
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.db.plans import SqlPlanRepository
from app.infrastructure.db.users import SqlUserRepository
from app.presentation.api.app import create_app
from app.presentation.composition import (
    database_engine,
    load_settings,
    recommend_courses,
    university_today,
)

settings = load_settings()
if settings.auth_jwt_secret is None:
    sys.exit("環境変数を確かめてください: AUTH_JWT_SECRET が設定されていません")
try:
    verifier = JwtVerifier(settings.auth_jwt_secret)
except ValueError as error:
    sys.exit(f"環境変数を確かめてください: AUTH_JWT_SECRET: {error}")
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
    identify=IdentifyUser(verifier, SqlUserRepository(engine)),
    curriculum_year=settings.curriculum_year,
    today=university_today,
)
