from typing import Annotated, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.recommendation import majority


class CurriculumSettings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    curriculum_year: int = 2026


class Settings(CurriculumSettings):
    database_url: str
    openai_api_key: SecretStr | None = None
    jev_api_key: SecretStr | None = None
    jev_model: str = "jev-1.14.0"
    auth_jwt_secret: SecretStr | None = None
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 1536
    search_by_skill: bool = True
    chat_model: str = "gpt-5.4-mini"
    occupation_reading_cache_size: Annotated[int, Field(ge=0, le=10_000)] = 500
    selection_model: str = "gpt-5.4-nano"
    selection_candidate_limit: Annotated[int, Field(gt=0, le=100)] = 20
    selection_votes: Annotated[int, Field(ge=1, le=5)] = 3
    selection_min_votes: Annotated[int, Field(ge=1, le=5)] | None = None
    selection_vote_delay_seconds: Annotated[float, Field(ge=0, le=10)] = 0.5
    semester_credit_limit: Annotated[int, Field(gt=0)] = 16
    openai_timeout_seconds: Annotated[float, Field(gt=0)] = 45
    openai_max_retries: Annotated[int, Field(ge=0)] = 1
    worker_poll_seconds: Annotated[float, Field(gt=0)] = 1
    plan_stall_minutes: Annotated[int, Field(gt=0)] = 20
    daily_plan_limit_per_user: Annotated[int, Field(gt=0)] = 3
    daily_plan_limit_total: Annotated[int, Field(gt=0)] = 30

    @property
    def selection_kept_votes(self) -> int:
        if self.selection_min_votes is None:
            return majority(self.selection_votes)
        return self.selection_min_votes

    @model_validator(mode="after")
    def _min_votes_within_votes(self) -> Self:
        if self.selection_min_votes is not None and self.selection_min_votes > self.selection_votes:
            raise ValueError(
                "SELECTION_MIN_VOTES は SELECTION_VOTES 以下にしてください: "
                f"{self.selection_min_votes} > {self.selection_votes}"
            )
        return self
