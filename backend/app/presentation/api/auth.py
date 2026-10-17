from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.identify_user import IdentifyUser


class MissingTokenError(Exception):
    pass


def current_user(identify: IdentifyUser) -> Callable[..., UUID]:
    bearer = HTTPBearer(auto_error=False)

    def user_id(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> UUID:
        if credentials is None:
            raise MissingTokenError("Authorization に Bearer の JWT がありません")
        return identify.run(credentials.credentials)

    return user_id
