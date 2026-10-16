from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from pydantic import SecretStr

from app.application.ports import InvalidTokenError
from app.infrastructure.auth.jwt_verifier import AUDIENCE, ISSUER, JwtVerifier

SECRET = "s" * 64
MINUTE = timedelta(minutes=1)


def token(secret: str = SECRET, algorithm: str = "HS256", **overrides: Any) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": "google-a",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 5 * MINUTE,
        **{key: value(now) if callable(value) else value for key, value in overrides.items()},
    }
    present = {key: value for key, value in claims.items() if value is not None}
    return jwt.encode(present, secret, algorithm)


def verify(encoded: str) -> str:
    return JwtVerifier(SecretStr(SECRET)).subject_of(encoded)


def test_a_valid_token_gives_its_subject_in_the_google_namespace() -> None:
    assert verify(token()) == "google:google-a"


def test_a_lifetime_one_second_over_from_rounding_is_tolerated() -> None:
    rounded = token(exp=lambda now: now + timedelta(seconds=301))

    assert verify(rounded) == "google:google-a"


def test_a_frontend_clock_a_little_ahead_is_tolerated() -> None:
    ahead = token(iat=lambda now: now + timedelta(seconds=10), exp=lambda now: now + 5 * MINUTE)

    assert verify(ahead) == "google:google-a"


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret": "t" * 64},
        {"algorithm": "HS512"},
        {"iss": "someone-else"},
        {"aud": "someone-else"},
        {"aud": [AUDIENCE, "someone-else"]},
        {"iat": lambda now: now - 10 * MINUTE, "exp": lambda now: now - 5 * MINUTE},
        {"iat": lambda now: now + 2 * MINUTE, "exp": lambda now: now + 6 * MINUTE},
        {
            "iat": lambda now: now + timedelta(seconds=20),
            "exp": lambda now: now - timedelta(seconds=10),
        },
        {"sub": None},
        {"sub": " "},
        {"sub": " 123 "},
        {"sub": "12\x003"},
        {"sub": "1" * 256},
        {"iat": None},
        {"exp": lambda now: now + timedelta(seconds=302)},
        {"iat": lambda now: str(int(now.timestamp()))},
        {"iat": True},
    ],
    ids=[
        "other-secret",
        "other-algorithm",
        "other-issuer",
        "other-audience",
        "audience-list",
        "expired",
        "issued-in-the-future",
        "expires-before-issued",
        "no-subject",
        "blank-subject",
        "subject-with-spaces",
        "subject-with-nul",
        "subject-too-long",
        "no-issued-at",
        "lives-too-long",
        "issued-at-as-text",
        "issued-at-as-bool",
    ],
)
def test_tokens_that_cannot_be_trusted_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(InvalidTokenError):
        verify(token(**overrides))


@pytest.mark.parametrize("bad", ["not-a-jwt", ""])
def test_strings_that_are_not_tokens_are_rejected(bad: str) -> None:
    with pytest.raises(InvalidTokenError):
        verify(bad)


def test_an_unsigned_token_is_rejected() -> None:
    now = datetime.now(UTC)
    claims = {"sub": "google-a", "iss": ISSUER, "aud": AUDIENCE, "iat": now, "exp": now + MINUTE}

    with pytest.raises(InvalidTokenError):
        verify(jwt.encode(claims, key="", algorithm="none"))


def test_only_hs256_is_accepted_even_with_the_right_key() -> None:
    with pytest.raises(InvalidTokenError, match="alg"):
        verify(token(algorithm="HS512"))


def test_a_short_secret_is_refused() -> None:
    with pytest.raises(ValueError, match="32 文字以上"):
        JwtVerifier(SecretStr("s" * 31))
