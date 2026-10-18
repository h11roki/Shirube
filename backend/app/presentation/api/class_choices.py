from collections.abc import Callable
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.application.list_class_choices import ListClassChoices
from app.domain.course import ALL_GRADES, Term
from app.domain.roadmap import Semester, term_on
from app.presentation.schemas.class_choices import ClassChoicesOut, class_choices_out
from app.presentation.schemas.plans import MAX_NAME_LENGTH


def class_choices_router(
    list_class_choices: ListClassChoices,
    current_user: Callable[..., UUID],
    curriculum_year: int,
    today: Callable[[], date],
) -> APIRouter:
    router = APIRouter()

    @router.get("/class-choices", dependencies=[Depends(current_user)])
    def show(
        department: Annotated[str, Query(min_length=1, max_length=MAX_NAME_LENGTH)],
        grade: Annotated[int, Query(ge=min(ALL_GRADES), le=max(ALL_GRADES))],
        term: Term | None = None,
    ) -> ClassChoicesOut:
        start = Semester(grade, term or term_on(today()))
        return class_choices_out(list_class_choices.run(department, curriculum_year, start))

    return router
