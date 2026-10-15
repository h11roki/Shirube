from logging.config import fileConfig
from typing import Literal

from alembic import context
from alembic.autogenerate.api import AutogenContext
from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine, pool

from app.infrastructure.db.models import Base
from app.settings import Settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
target_metadata = Base.metadata


def render_vector(type_: str, obj: object, autogen_context: AutogenContext) -> str | Literal[False]:
    if type_ == "type" and isinstance(obj, Vector):
        autogen_context.imports.add("from pgvector.sqlalchemy import Vector")
        return f"Vector({obj.dim})"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=Settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(Settings().database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_item=render_vector
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
