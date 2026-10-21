from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.application.delete_account import DeleteAccount
from app.presentation.schemas.errors import BUSY_RESPONSE


def me_router(delete_account: DeleteAccount, current_user: Callable[..., UUID]) -> APIRouter:
    router = APIRouter()

    @router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, responses=BUSY_RESPONSE)
    def leave(user_id: Annotated[UUID, Depends(current_user)]) -> None:
        delete_account.run(user_id)

    return router
