from uuid import UUID, uuid4

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DbSession

from app.infrastructure.db.models import UserRow


class SqlUserRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def id_of(self, subject: str) -> UUID:
        by_subject = select(UserRow.id).where(UserRow.subject == subject)
        with DbSession(self._engine) as db:
            existing = db.execute(by_subject).scalar_one_or_none()
            if existing is not None:
                return existing
            created = db.execute(
                insert(UserRow)
                .values(id=uuid4(), subject=subject)
                .on_conflict_do_nothing(index_elements=[UserRow.subject])
                .returning(UserRow.id)
            ).scalar_one_or_none()
            user_id = created if created is not None else db.execute(by_subject).scalar_one()
            db.commit()
            return user_id
