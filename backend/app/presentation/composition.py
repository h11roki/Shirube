import importlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import SecretStr, ValidationError
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import ArgumentError

from app.application.build_plans import BuildPlans
from app.application.cached_occupation_analyzer import CachedOccupationAnalyzer
from app.application.cached_recommender import CachedRecommender
from app.application.fingerprint import fingerprint_of
from app.application.ports import CourseSelector, OccupationAnalyzer, ReasonJudge
from app.application.recommend_courses import RecommendCourses, Recommender
from app.application.report_plan_builds import ReportPlanBuilds
from app.application.request_plan import RequestPlan
from app.application.search_courses import (
    SearchCourses,
    SearchQueries,
    query_and_skills,
    whole_query,
)
from app.application.tidy_daily import TidyDaily
from app.application.voting_course_selector import VotingCourseSelector
from app.domain.quota import PlanQuota
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.db.models import EMBEDDING_DIMENSIONS
from app.infrastructure.db.plan_builds import SqlPlanBuildLog
from app.infrastructure.db.plans import SqlPlanRepository
from app.infrastructure.db.recommendations import SqlRecommendationStore
from app.infrastructure.db.users import SqlUserRepository
from app.infrastructure.llm.openai_course_selector import INSTRUCTIONS as SELECTION_INSTRUCTIONS
from app.infrastructure.llm.openai_course_selector import OpenAICourseSelector
from app.infrastructure.llm.openai_embedder import OpenAIEmbedder
from app.infrastructure.llm.openai_occupation_analyzer import OpenAIOccupationAnalyzer
from app.infrastructure.llm.openai_reason_judge import OpenAIReasonJudge
from app.infrastructure.llm.usage_meter import LangChainUsageMeter
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
        return create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True)
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
        selector,
        settings.selection_votes,
        settings.selection_kept_votes,
        settings.selection_vote_delay_seconds,
    )


def reason_judge(settings: Settings) -> ReasonJudge:
    return OpenAIReasonJudge.connect(
        settings.reason_judge_model,
        openai_api_key(settings),
        settings.openai_timeout_seconds,
        settings.openai_max_retries,
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


RECOMMENDING_MODULES = (
    "app.domain.occupation",
    "app.domain.ranking",
    "app.domain.recommendation",
    "app.domain.excerpts",
    "app.application.search_courses",
    "app.application.recommend_courses",
    "app.application.voting_course_selector",
    "app.infrastructure.llm.openai_embedder",
    "app.infrastructure.llm.openai_occupation_analyzer",
    "app.infrastructure.llm.openai_course_selector",
)


def recommendation_fingerprint(settings: Settings) -> str:
    sources = [
        Path(str(importlib.import_module(name).__file__)).read_text(encoding="utf-8")
        for name in RECOMMENDING_MODULES
    ]
    parts = (
        settings.chat_model,
        settings.selection_model,
        settings.embedding_model,
        str(settings.embedding_dimensions),
        str(settings.search_by_skill),
        str(settings.selection_candidate_limit),
        str(settings.selection_votes),
        str(settings.selection_kept_votes),
        *sources,
    )
    return fingerprint_of(parts)[:16]


def recommender(settings: Settings, engine: Engine) -> Recommender:
    recommend = recommend_courses(settings, engine)
    if settings.recommendation_cache_days == 0:
        return recommend
    return CachedRecommender(
        recommend,
        SqlRecommendationStore(engine),
        SqlCourseRepository(engine),
        recommendation_fingerprint(settings),
        timedelta(days=settings.recommendation_cache_days),
        now,
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
        recommender(settings, engine),
        SqlCourseRepository(engine),
        SqlPlanRepository(engine),
        SqlUserRepository(engine),
        SqlPlanBuildLog(engine),
        LangChainUsageMeter(),
    )


def tidy_daily(engine: Engine) -> TidyDaily:
    return TidyDaily(SqlPlanRepository(engine), SqlRecommendationStore(engine), now)


def report_plan_builds(engine: Engine) -> ReportPlanBuilds:
    return ReportPlanBuilds(SqlPlanBuildLog(engine), now)


def now() -> datetime:
    return datetime.now(UTC)
