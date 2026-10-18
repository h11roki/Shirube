import sys

from app.application.get_plan import GetPlan
from app.application.identify_user import IdentifyUser
from app.infrastructure.auth.jwt_verifier import JwtVerifier
from app.infrastructure.db.plans import SqlPlanRepository
from app.infrastructure.db.users import SqlUserRepository
from app.presentation.api.app import create_app
from app.presentation.composition import (
    database_engine,
    load_settings,
    request_plan,
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
app = create_app(
    request_plan=request_plan(settings, engine),
    get_plan=GetPlan(SqlPlanRepository(engine)),
    identify=IdentifyUser(verifier, SqlUserRepository(engine)),
    curriculum_year=settings.curriculum_year,
    today=university_today,
)
