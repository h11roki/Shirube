from typing import Any

from fastapi import status
from pydantic import BaseModel


class ErrorOut(BaseModel):
    detail: str


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorOut, "description": "ログインしていない"},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorOut, "description": "サーバー側の問題"},
}
INVALID_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorOut,
        "description": "リクエストを直せば通る誤り",
    }
}
CONFLICT_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {
        "model": ErrorOut,
        "description": "道標が完了していない、時間割表が変わった、ほかの画面で答えが変わった",
    }
}
NOT_FOUND_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": ErrorOut, "description": "無いか、ほかの利用者の道標"}
}
