from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from pydantic import SecretStr

from app.application.ports import InvalidTokenError
from app.infrastructure.auth.jwt_verifier import AUDIENCE, ISSUER, JwtVerifier

SECRET = "s" * 32
NOW = datetime.now(UTC)


def token(secret: str = SECRET, algorithm: str = "HS256", **overrides: Any) -> str:
    claims = {
        "sub": "google-a",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": NOW,
        "exp": NOW + timedelta(minutes=5),
        **overrides,
    }
    return jwt.encode(
        {key: value for key, value in claims.items() if value is not None}, secret, algorithm
    )


def test_a_valid_token_gives_its_subject() -> None:
    assert JwtVerifier(SecretStr(SECRET)).subject_of(token()) == "google-a"


@pytest.mark.parametrize(
    "bad",
    [
        token(secret="t" * 32),
        token(secret="s" * 64, algorithm="HS512"),
        token(iss="someone-else"),
        token(aud="someone-else"),
        token(iat=NOW - timedelta(minutes=10), exp=NOW - timedelta(minutes=5)),
        token(sub=None),
        token(iat=None),
        token(exp=NOW + timedelta(minutes=6)),
        "not-a-jwt",
    ],
    ids=[
        "other-secret",
        "other-algorithm",
        "other-issuer",
        "other-audience",
        "expired",
        "no-subject",
        "no-issued-at",
        "lives-too-long",
        "garbage",
    ],
)
def test_tokens_that_cannot_be_trusted_are_rejected(bad: str) -> None:
    with pytest.raises(InvalidTokenError):
        JwtVerifier(SecretStr(SECRET)).subject_of(bad)


def test_an_unsigned_token_is_rejected() -> None:
    unsigned = jwt.encode(
        {
            "sub": "google-a",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": NOW,
            "exp": NOW + timedelta(minutes=5),
        },
        key="",
        algorithm="none",
    )

    with pytest.raises(InvalidTokenError):
        JwtVerifier(SecretStr(SECRET)).subject_of(unsigned)
