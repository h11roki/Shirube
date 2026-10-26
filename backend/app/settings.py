from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _prompt_text(path: object) -> str | None:
    if path is None:
        return None
    try:
        text = Path(str(path)).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"選び直しの指示文のファイルを読めません: {error}") from error
    if not text:
        raise ValueError("選び直しの指示文のファイルが空です")
    return text


class CurriculumSettings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    curriculum_year: int = 2026


class Settings(CurriculumSettings):
    database_url: str
    openai_api_key: SecretStr | None = None
    auth_jwt_secret: SecretStr | None = None
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 1536
    search_by_skill: bool = True
    chat_model: str = "gpt-5.4-mini"
    occupation_reading_cache_size: Annotated[int, Field(ge=0, le=10_000)] = 500
    selection_model: str = "gpt-5.4-nano"
    selection_candidate_limit: Annotated[int, Field(gt=0, le=100)] = 20
    selection_votes: Annotated[int, Field(ge=1, le=5)] = 3
    selection_vote_delay_seconds: Annotated[float, Field(ge=0, le=10)] = 0.5
    selection_prompt: Annotated[str | None, BeforeValidator(_prompt_text)] = None
    semester_credit_limit: Annotated[int, Field(gt=0)] = 16
    openai_timeout_seconds: Annotated[float, Field(gt=0)] = 45
    openai_max_retries: Annotated[int, Field(ge=0)] = 1
    worker_poll_seconds: Annotated[float, Field(gt=0)] = 1
    plan_stall_minutes: Annotated[int, Field(gt=0)] = 20
    daily_plan_limit_per_user: Annotated[int, Field(gt=0)] = 3
    daily_plan_limit_total: Annotated[int, Field(gt=0)] = 30
