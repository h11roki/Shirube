from pydantic import BaseModel

from app.domain.course import Term


class ClassChoiceOut(BaseModel):
    name: str
    class_codes: list[str]


class ClassChoicesOut(BaseModel):
    term: Term
    courses: list[ClassChoiceOut]
