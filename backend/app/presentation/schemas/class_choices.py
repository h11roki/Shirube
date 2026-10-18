from pydantic import BaseModel

from app.domain.course import Term
from app.domain.roadmap import ClassChoice


class ClassChoiceOut(BaseModel):
    name: str
    class_codes: list[str]


class ClassChoicesOut(BaseModel):
    term: Term
    courses: list[ClassChoiceOut]


def class_choices_out(term: Term, choices: list[ClassChoice]) -> ClassChoicesOut:
    return ClassChoicesOut(
        term=term,
        courses=[
            ClassChoiceOut(name=choice.name, class_codes=list(choice.class_codes))
            for choice in choices
        ],
    )
