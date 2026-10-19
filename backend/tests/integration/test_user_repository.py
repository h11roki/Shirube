from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, func, select

from app.infrastructure.db.models import TakenCourseRow, UserRow
from app.infrastructure.db.users import SqlUserRepository


@pytest.fixture
def users(engine: Engine) -> Iterator[SqlUserRepository]:
    yield SqlUserRepository(engine)
    with engine.begin() as connection:
        connection.execute(delete(TakenCourseRow))
        connection.execute(delete(UserRow))


def test_a_subject_gets_one_user_that_is_created_on_first_use(
    engine: Engine, users: SqlUserRepository
) -> None:
    first = users.id_of("google-a")

    assert users.id_of("google-a") == first
    assert users.id_of("google-b") != first
    with engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(UserRow)).scalar_one() == 2


def test_taken_courses_are_added_and_removed_one_by_one_for_each_user(
    engine: Engine, users: SqlUserRepository
) -> None:
    user = users.id_of("google-a")
    other = users.id_of("google-b")
    users.add_taken(other, "科目A")
    users.add_taken(user, "科目A")
    users.add_taken(user, "科目A")
    users.add_taken(user, "科目B")

    users.remove_taken(user, "科目A")
    users.remove_taken(user, "科目C")

    assert users.taken(user) == {"科目B"}
    assert users.taken(other) == {"科目A"}
    assert users.taken(uuid4()) == frozenset()
