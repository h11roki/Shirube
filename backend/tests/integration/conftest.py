import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Engine, create_engine, make_url, text

ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"
TEST_DATABASE_SUFFIX = "_test"


@pytest.fixture(scope="session")
def test_url() -> URL:
    url = os.environ.get("DATABASE_URL")
    if url is None:
        pytest.skip("DATABASE_URL が無い")
    server = make_url(url)
    test_url = server.set(database=f"{server.database}{TEST_DATABASE_SUFFIX}")
    admin = create_engine(server, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{test_url.database}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    admin.dispose()
    return test_url


@pytest.fixture(scope="session")
def alembic_config(test_url: URL) -> Config:
    config = Config(str(ALEMBIC_INI))
    rendered = test_url.render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", rendered.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def engine(test_url: URL, alembic_config: Config) -> Iterator[Engine]:
    command.upgrade(alembic_config, "head")
    engine = create_engine(test_url)
    yield engine
    engine.dispose()
