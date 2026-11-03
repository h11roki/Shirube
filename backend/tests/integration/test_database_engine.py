from collections.abc import Iterator

import pytest
from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.exc import DBAPIError

from app.presentation.composition import database_engine
from app.settings import Settings

TERMINATE_WAIT_MS = 5000


@pytest.fixture
def app_engine(test_url: URL) -> Iterator[Engine]:
    engine = database_engine(Settings(database_url=test_url.render_as_string(hide_password=False)))
    yield engine
    engine.dispose()


def test_a_pooled_connection_the_database_closed_is_replaced_before_the_next_query(
    test_url: URL, app_engine: Engine
) -> None:
    with app_engine.connect() as connection:
        closed = connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
    admin = create_engine(test_url)
    with admin.connect() as connection:
        terminated = connection.execute(
            text("SELECT pg_terminate_backend(:pid, :wait)"),
            {"pid": closed, "wait": TERMINATE_WAIT_MS},
        ).scalar_one()
    admin.dispose()

    with app_engine.connect() as connection:
        assert terminated
        assert connection.execute(text("SELECT pg_backend_pid()")).scalar_one() != closed


def test_a_failed_query_keeps_its_parameters_out_of_the_error(app_engine: Engine) -> None:
    with pytest.raises(DBAPIError) as raised, app_engine.connect() as connection:
        connection.execute(text("SELECT CAST(:subject AS text), 1 / 0"), {"subject": "google:1234"})

    assert "google:1234" not in str(raised.value)
