import jwt
from pydantic import SecretStr

from app.application.ports import InvalidTokenError

ALGORITHM = "HS256"
ISSUER = "shirube-frontend"
AUDIENCE = "shirube-backend"
MAX_LIFETIME_SECONDS = 300
REQUIRED_CLAIMS = ["sub", "iss", "aud", "iat", "exp"]


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
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWTError as error:
            raise InvalidTokenError(f"JWT を確かめられません: {error}") from error
        if claims["exp"] - claims["iat"] > MAX_LIFETIME_SECONDS:
            raise InvalidTokenError(f"JWT の有効期間が {MAX_LIFETIME_SECONDS} 秒を超えています")
        subject: str = claims["sub"]
        return subject
