import sys

from app.application.answer_taken_courses import AnswerTakenCourses
from app.application.delete_account import DeleteAccount
from app.application.delete_plan import DeletePlan
from app.application.get_plan import GetPlan
from app.application.identify_user import IdentifyUser
from app.application.list_class_choices import ListClassChoices
from app.application.list_plans import ListPlans
from app.application.syllabus_links import SyllabusLinks
from app.application.taken_courses import TakenCourses
from app.infrastructure.auth.jwt_verifier import JwtVerifier
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.db.plans import SqlPlanRepository
from app.infrastructure.db.users import SqlUserRepository
from app.presentation.api.app import create_app
from app.presentation.composition import (
    database_engine,
    load_settings,
    now,
    request_plan,
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
courses = SqlCourseRepository(engine)
users = SqlUserRepository(engine)
app = create_app(
    request_plan=request_plan(settings, engine),
    get_plan=GetPlan(plans),
    list_plans=ListPlans(plans),
    list_class_choices=ListClassChoices(courses, users),
    answer_taken_courses=AnswerTakenCourses(plans, users, courses),
    delete_plan=DeletePlan(plans, now),
    syllabus_links=SyllabusLinks(courses),
    taken_courses=TakenCourses(users),
    delete_account=DeleteAccount(users, now),
    identify=IdentifyUser(verifier, users),
    curriculum_year=settings.curriculum_year,
)
