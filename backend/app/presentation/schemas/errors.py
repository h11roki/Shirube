from typing import Any

from fastapi import status
from pydantic import BaseModel


class ErrorOut(BaseModel):
    detail: str


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorOut, "description": "ログインしていない"},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorOut,
        "description": "リクエストを直せば通る誤り",
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorOut, "description": "サーバー側の問題"},
}
NOT_FOUND_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": ErrorOut, "description": "無いか、ほかの利用者の道標"}
}
