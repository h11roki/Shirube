import traceback
from collections.abc import Iterator
from contextlib import ExitStack

import pytest
from psycopg.errors import DivisionByZero
from sqlalchemy import URL, Engine, text
from sqlalchemy.exc import DataError

from app.presentation.composition import database_engine
from app.settings import Settings

TERMINATE_WAIT_MS = 5000
SUBJECT = "google:1234"
POOLED_CONNECTIONS = 2


@pytest.fixture
def app_engine(test_url: URL) -> Iterator[Engine]:
    engine = database_engine(Settings(database_url=test_url.render_as_string(hide_password=False)))
    yield engine
    engine.dispose()


def backend_pids(engine: Engine) -> set[int]:
    with ExitStack() as stack:
        connections = [stack.enter_context(engine.connect()) for _ in range(POOLED_CONNECTIONS)]
        return {
            connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
            for connection in connections
        }


def test_pooled_connections_the_database_closed_are_replaced_before_the_next_queries(
    engine: Engine, app_engine: Engine
) -> None:
    closed = backend_pids(app_engine)
    with engine.connect() as connection:
        terminated = [
            connection.execute(
                text("SELECT pg_terminate_backend(:pid, :wait)"),
                {"pid": pid, "wait": TERMINATE_WAIT_MS},
            ).scalar_one()
            for pid in closed
        ]
    assert terminated == [True] * POOLED_CONNECTIONS

    assert backend_pids(app_engine).isdisjoint(closed)


def test_the_logged_traceback_of_a_failed_query_leaves_out_its_parameters(
    app_engine: Engine,
) -> None:
    with app_engine.connect() as connection, pytest.raises(DataError) as raised:
        connection.execute(text("SELECT CAST(:subject AS text), 1 / 0"), {"subject": SUBJECT})

    assert isinstance(raised.value.orig, DivisionByZero)
    assert SUBJECT not in "".join(traceback.format_exception(raised.value))
