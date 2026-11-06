from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, create_engine

from app.application.ports import StorageUnavailableError
from app.infrastructure.db.plan_builds import SqlPlanBuildLog
from app.infrastructure.db.plans import SqlPlanRepository

UNREACHABLE = "postgresql+psycopg://shirube:shirube@127.0.0.1:1/none"


@pytest.mark.parametrize(
    "read",
    [
        lambda engine: SqlPlanRepository(engine).oldest_waiting(),
        lambda engine: SqlPlanBuildLog(engine).since(datetime(2026, 11, 1, tzinfo=UTC)),
    ],
    ids=["oldest-waiting", "builds-since"],
)
def test_an_unreachable_database_is_a_storage_error(read: Callable[[Engine], object]) -> None:
    engine = create_engine(UNREACHABLE)
    try:
        with pytest.raises(StorageUnavailableError, match="127.0.0.1"):
            read(engine)
    finally:
        engine.dispose()
