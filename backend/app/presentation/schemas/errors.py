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
BUSY_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {"model": ErrorOut, "description": "作っている道標がある"}
}
LIMIT_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": ErrorOut,
        "description": "1 人か全体の、1 日に作れる数に達した",
        "headers": {
            "Retry-After": {
                "description": "次の日本時間の 0 時までの秒数",
                "schema": {"type": "integer"},
            }
        },
    }
}
NOT_FOUND_RESPONSE: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": ErrorOut, "description": "無いか、ほかの利用者の道標"}
}
