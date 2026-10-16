import sys
from datetime import date, datetime, timedelta, timezone

from pydantic import SecretStr, ValidationError
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import ArgumentError

from app.application.recommend_courses import RecommendCourses
from app.application.search_courses import SearchCourses
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.db.models import EMBEDDING_DIMENSIONS
from app.infrastructure.llm.openai_course_selector import OpenAICourseSelector
from app.infrastructure.llm.openai_embedder import OpenAIEmbedder
from app.infrastructure.llm.openai_occupation_analyzer import OpenAIOccupationAnalyzer
from app.settings import Settings

UNIVERSITY_TIME = timezone(timedelta(hours=9))


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        problems = "; ".join(
            f"{str(problem['loc'][0]).upper() if problem['loc'] else '設定'}: {problem['msg']}"
            for problem in error.errors()
        )
        sys.exit(f"環境変数を確かめてください: {problems}")


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
    return OpenAIEmbedder(settings.embedding_model, settings.embedding_dimensions, api_key)


def openai_occupation_analyzer(settings: Settings) -> OpenAIOccupationAnalyzer:
    return OpenAIOccupationAnalyzer.connect(settings.chat_model, openai_api_key(settings))


def openai_course_selector(settings: Settings) -> OpenAICourseSelector:
    return OpenAICourseSelector.connect(settings.selection_model, openai_api_key(settings))


def recommend_courses(settings: Settings, engine: Engine) -> RecommendCourses:
    courses = SqlCourseRepository(engine)
    search = SearchCourses(courses, SqlChunkRepository(engine), openai_embedder(settings))
    return RecommendCourses(
        search,
        courses,
        openai_occupation_analyzer(settings),
        openai_course_selector(settings),
        settings.selection_candidate_limit,
    )


def university_today() -> date:
    return datetime.now(UNIVERSITY_TIME).date()
