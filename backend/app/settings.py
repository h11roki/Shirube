from typing import Annotated

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    database_url: str
    openai_api_key: SecretStr | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    chat_model: str = "gpt-5.4-mini"
    selection_model: str = "gpt-5.4-nano"
    selection_candidate_limit: Annotated[int, Field(gt=0, le=100)] = 30
    semester_credit_limit: Annotated[int, Field(gt=0)] = 16
    curriculum_year: int = 2026
