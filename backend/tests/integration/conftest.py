import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine

ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = os.environ.get("DATABASE_URL")
    if url is None:
        pytest.skip("DATABASE_URL が無い")
    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    engine = create_engine(url)
    yield engine
    engine.dispose()
