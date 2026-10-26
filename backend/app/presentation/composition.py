import sys
from datetime import UTC, date, datetime
from typing import Any

from pydantic import SecretStr, ValidationError
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import ArgumentError

from app.application.build_plans import BuildPlans
from app.application.cached_occupation_analyzer import CachedOccupationAnalyzer
from app.application.forget_deleted_plans import ForgetDeletedPlans
from app.application.ports import CourseSelector, OccupationAnalyzer
from app.application.recommend_courses import RecommendCourses
from app.application.request_plan import RequestPlan
from app.application.search_courses import (
    SearchCourses,
    SearchQueries,
    query_and_skills,
    whole_query,
)
from app.application.voting_course_selector import VotingCourseSelector
from app.domain.course import UNIVERSITY_TIME
from app.domain.quota import PlanQuota
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.db.models import EMBEDDING_DIMENSIONS
from app.infrastructure.db.plans import SqlPlanRepository
from app.infrastructure.db.users import SqlUserRepository
from app.infrastructure.llm.openai_course_selector import INSTRUCTIONS as SELECTION_INSTRUCTIONS
from app.infrastructure.llm.openai_course_selector import OpenAICourseSelector
from app.infrastructure.llm.openai_embedder import OpenAIEmbedder
from app.infrastructure.llm.openai_occupation_analyzer import OpenAIOccupationAnalyzer
from app.settings import Settings


def load_settings(**overrides: Any) -> Settings:
    try:
        return Settings(**overrides)
    except ValidationError as error:
        problems = "; ".join(
            f"{str(problem['loc'][0]).upper() if problem['loc'] else '設定'}: {problem['msg']}"
            for problem in error.errors()
        )
        source = "環境変数か、指定した設定" if overrides else "環境変数"
        sys.exit(f"{source}を確かめてください: {problems}")


def database_engine(settings: Settings) -> Engine:
    try:
        return create_engine(settings.database_url)
    except ArgumentError as error:
        sys.exit(f"DATABASE_URL を読めません: {error}")


def openai_api_key(settings: Settings) -> SecretStr:
    if settings.openai_api_key is None:
        sys.exit("環境変数を確かめてください: OPENAI_API_KEY が設定されていません")
    return settings.openai_api_key


def openai_embedder(settings: Settings) -> OpenAIEmbedder:
    api_key = openai_api_key(settings)
    if settings.embedding_dimensions != EMBEDDING_DIMENSIONS:
        sys.exit(
            f"EMBEDDING_DIMENSIONS {settings.embedding_dimensions} が DB の列の "
            f"{EMBEDDING_DIMENSIONS} と違います。列を変えるマイグレーションが要ります"
        )
    return OpenAIEmbedder.connect(
        settings.embedding_model,
        settings.embedding_dimensions,
        api_key,
        settings.openai_timeout_seconds,
        settings.openai_max_retries,
    )


def openai_occupation_analyzer(settings: Settings) -> OpenAIOccupationAnalyzer:
    return OpenAIOccupationAnalyzer.connect(
        settings.chat_model,
        openai_api_key(settings),
        settings.openai_timeout_seconds,
        settings.openai_max_retries,
    )


def occupation_analyzer(settings: Settings) -> OccupationAnalyzer:
    analyzer = openai_occupation_analyzer(settings)
    if settings.occupation_reading_cache_size == 0:
        return analyzer
    return CachedOccupationAnalyzer(analyzer, settings.occupation_reading_cache_size)


def course_selector(
    settings: Settings, instructions: str = SELECTION_INSTRUCTIONS
) -> CourseSelector:
    selector = OpenAICourseSelector.connect(
        settings.selection_model,
        openai_api_key(settings),
        settings.openai_timeout_seconds,
        settings.openai_max_retries,
        instructions,
    )
    if settings.selection_votes == 1:
        return selector
    return VotingCourseSelector(
        selector, settings.selection_votes, settings.selection_vote_delay_seconds
    )


def search_queries(settings: Settings) -> SearchQueries:
    return query_and_skills if settings.search_by_skill else whole_query


def search_courses(settings: Settings, engine: Engine) -> SearchCourses:
    return SearchCourses(
        SqlCourseRepository(engine),
        SqlChunkRepository(engine),
        openai_embedder(settings),
        search_queries(settings),
    )


def recommend_courses(settings: Settings, engine: Engine) -> RecommendCourses:
    return RecommendCourses(
        search_courses(settings, engine),
        SqlCourseRepository(engine),
        occupation_analyzer(settings),
        course_selector(settings),
        settings.selection_candidate_limit,
    )


def request_plan(settings: Settings, engine: Engine) -> RequestPlan:
    return RequestPlan(
        search_courses(settings, engine),
        SqlCourseRepository(engine),
        SqlPlanRepository(engine),
        SqlUserRepository(engine),
        settings.semester_credit_limit,
        PlanQuota(settings.daily_plan_limit_per_user, settings.daily_plan_limit_total),
        now,
    )


def build_plans(settings: Settings, engine: Engine) -> BuildPlans:
    return BuildPlans(
        recommend_courses(settings, engine),
        SqlCourseRepository(engine),
        SqlPlanRepository(engine),
        SqlUserRepository(engine),
    )


def forget_deleted_plans(engine: Engine) -> ForgetDeletedPlans:
    return ForgetDeletedPlans(SqlPlanRepository(engine), now)


def now() -> datetime:
    return datetime.now(UTC)


def university_today() -> date:
    return datetime.now(UNIVERSITY_TIME).date()
