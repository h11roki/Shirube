from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, delete, func, select

from app.infrastructure.db.models import UserRow
from app.infrastructure.db.users import SqlUserRepository


@pytest.fixture
def users(engine: Engine) -> Iterator[SqlUserRepository]:
    yield SqlUserRepository(engine)
    with engine.begin() as connection:
        connection.execute(delete(UserRow))


def test_a_subject_gets_one_user_that_is_created_on_first_use(
    engine: Engine, users: SqlUserRepository
) -> None:
    first = users.id_of("google-a")

    assert users.id_of("google-a") == first
    assert users.id_of("google-b") != first
    with engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(UserRow)).scalar_one() == 2
