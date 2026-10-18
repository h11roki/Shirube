from pydantic import BaseModel

from app.domain.roadmap import ClassChoice


class ClassChoiceOut(BaseModel):
    name: str
    class_codes: list[str]


class ClassChoicesOut(BaseModel):
    courses: list[ClassChoiceOut]


def class_choices_out(choices: list[ClassChoice]) -> ClassChoicesOut:
    return ClassChoicesOut(
        courses=[
            ClassChoiceOut(name=choice.name, class_codes=list(choice.class_codes))
            for choice in choices
        ]
    )
