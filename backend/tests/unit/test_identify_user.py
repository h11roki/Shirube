import pytest

from app.application.identify_user import IdentifyUser
from app.application.ports import InvalidTokenError
from tests.fakes import TOKENS, FakeTokenVerifier, FakeUserRepository


def test_the_user_is_looked_up_by_the_subject_of_the_token() -> None:
    users = FakeUserRepository()

    user_id = IdentifyUser(FakeTokenVerifier(TOKENS), users).run("token-a")

    assert users.users == {"google-a": user_id}


def test_a_token_that_cannot_be_verified_creates_no_user() -> None:
    users = FakeUserRepository()

    with pytest.raises(InvalidTokenError):
        IdentifyUser(FakeTokenVerifier(TOKENS), users).run("token-z")
    assert users.users == {}
