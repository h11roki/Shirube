from typing import Annotated

from fastapi import Path
from pydantic import BaseModel

from app.presentation.schemas.plans import MAX_NAME_LENGTH

TakenCourseName = Annotated[str, Path(max_length=MAX_NAME_LENGTH)]


class TakenCoursesOut(BaseModel):
    names: list[str]
