from collections.abc import Iterator

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

    with engine.connect() as connection:
        rows = connection.execute(select(TakenCourseRow.user_id, TakenCourseRow.name)).all()
    assert sorted((str(user_id), name) for user_id, name in rows) == sorted(
        [(str(other), "科目A"), (str(user), "科目B")]
    )
