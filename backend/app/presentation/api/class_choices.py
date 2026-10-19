from collections.abc import Callable
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.application.list_class_choices import ListClassChoices
from app.domain.course import ALL_GRADES, Term
from app.domain.roadmap import Semester, term_on
from app.presentation.schemas.class_choices import ClassChoiceOut, ClassChoicesOut
from app.presentation.schemas.errors import INVALID_RESPONSE
from app.presentation.schemas.plans import DepartmentName


def class_choices_router(
    list_class_choices: ListClassChoices,
    current_user: Callable[..., UUID],
    curriculum_year: int,
    today: Callable[[], date],
) -> APIRouter:
    router = APIRouter()

    @router.get("/class-choices", responses=INVALID_RESPONSE)
    def show(
        department: Annotated[DepartmentName, Query()],
        grade: Annotated[int, Query(ge=min(ALL_GRADES), le=max(ALL_GRADES))],
        user_id: Annotated[UUID, Depends(current_user)],
        term: Term | None = None,
    ) -> ClassChoicesOut:
        start = Semester(grade, term or term_on(today()))
        return ClassChoicesOut(
            term=start.term,
            courses=[
                ClassChoiceOut(name=choice.name, class_codes=list(choice.class_codes))
                for choice in list_class_choices.run(user_id, department, curriculum_year, start)
            ],
        )

    return router
