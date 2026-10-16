from uuid import UUID, uuid4

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DbSession

from app.infrastructure.db.models import UserRow


class SqlUserRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def id_of(self, subject: str) -> UUID:
        with DbSession(self._engine) as db, db.begin():
            db.execute(
                insert(UserRow)
                .values(id=uuid4(), subject=subject)
                .on_conflict_do_nothing(index_elements=[UserRow.subject])
            )
            return db.execute(select(UserRow.id).where(UserRow.subject == subject)).scalar_one()
