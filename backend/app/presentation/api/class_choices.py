from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.application.list_class_choices import ListClassChoices
from app.presentation.api.start_query import StartQuery, start_query
from app.presentation.schemas.class_choices import ClassChoiceOut, ClassChoicesOut
from app.presentation.schemas.errors import INVALID_RESPONSE


def class_choices_router(
    list_class_choices: ListClassChoices,
    current_user: Callable[..., UUID],
    curriculum_year: int,
) -> APIRouter:
    router = APIRouter()

    @router.get("/class-choices", responses=INVALID_RESPONSE)
    def show(
        query: Annotated[StartQuery, Depends(start_query)],
        user_id: Annotated[UUID, Depends(current_user)],
    ) -> ClassChoicesOut:
        choices = list_class_choices.run(user_id, query.department, curriculum_year, query.start)
        return ClassChoicesOut(
            term=query.start.term,
            courses=[
                ClassChoiceOut(name=choice.name, class_codes=list(choice.class_codes))
                for choice in choices
            ],
        )

    return router
