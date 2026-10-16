import re

import jwt
from pydantic import SecretStr

from app.application.ports import InvalidTokenError

ALGORITHM = "HS256"
ISSUER = "shirube-frontend"
AUDIENCE = "shirube-backend"
MIN_SECRET_LENGTH = 32
MAX_LIFETIME_SECONDS = 300
ROUNDING_SECONDS = 1
LEEWAY_SECONDS = 30
REQUIRED_CLAIMS = ["sub", "iss", "aud", "iat", "exp"]
SUBJECT_PREFIX = "google:"
SUBJECT = re.compile(r"[\x21-\x7e]{1,255}")


class JwtVerifier:
    def __init__(self, secret: SecretStr) -> None:
        if len(secret.get_secret_value()) < MIN_SECRET_LENGTH:
            raise ValueError(f"JWT の鍵は {MIN_SECRET_LENGTH} 文字以上にしてください")
        self._secret = secret

    def subject_of(self, token: str) -> str:
        try:
            claims = jwt.decode(
                token,
                self._secret.get_secret_value(),
                algorithms=[ALGORITHM],
                audience=AUDIENCE,
                issuer=ISSUER,
                leeway=LEEWAY_SECONDS,
                options={"require": REQUIRED_CLAIMS, "strict_aud": True},
            )
        except jwt.PyJWTError as error:
            raise InvalidTokenError(f"JWT を確かめられません: {error}") from error
        issued, expires, subject = claims["iat"], claims["exp"], claims["sub"]
        if not all(type(moment) is int for moment in (issued, expires)):
            raise InvalidTokenError("JWT の iat と exp は整数の秒にしてください")
        if not 0 < expires - issued <= MAX_LIFETIME_SECONDS + ROUNDING_SECONDS:
            raise InvalidTokenError(
                f"JWT の有効期間は 0 秒より長く {MAX_LIFETIME_SECONDS} 秒以下にしてください"
            )
        if not SUBJECT.fullmatch(subject):
            raise InvalidTokenError("JWT の sub は空白の無い ASCII の 255 文字までにしてください")
        return f"{SUBJECT_PREFIX}{subject}"
