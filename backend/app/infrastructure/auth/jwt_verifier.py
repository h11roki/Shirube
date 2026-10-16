import jwt
from pydantic import SecretStr

from app.application.ports import InvalidTokenError

ALGORITHM = "HS256"
ISSUER = "shirube-frontend"
AUDIENCE = "shirube-backend"
MAX_LIFETIME_SECONDS = 300
LEEWAY_SECONDS = 30
REQUIRED_CLAIMS = ["sub", "iss", "aud", "iat", "exp"]
SUBJECT_PREFIX = "google:"


class JwtVerifier:
    def __init__(self, secret: SecretStr) -> None:
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
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWTError as error:
            raise InvalidTokenError(f"JWT を確かめられません: {error}") from error
        issued, expires, subject = claims["iat"], claims["exp"], claims["sub"]
        if not all(type(moment) is int for moment in (issued, expires)):
            raise InvalidTokenError("JWT の iat と exp は整数の秒にしてください")
        if expires - issued > MAX_LIFETIME_SECONDS:
            raise InvalidTokenError(f"JWT の有効期間が {MAX_LIFETIME_SECONDS} 秒を超えています")
        if not subject.strip():
            raise InvalidTokenError("JWT の sub が空です")
        return f"{SUBJECT_PREFIX}{subject}"
