from typing import Literal

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: Literal["ok", "degraded", "down"]
    version: str
    database: Literal["ok", "down"]
    queue: Literal["ok", "stalled", "unknown"]
    openai: Literal["ok", "out_of_credit", "unknown"]
