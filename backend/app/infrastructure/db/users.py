from uuid import UUID, uuid4

from sqlalchemy import Engine, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DbSession

from app.infrastructure.db.models import TakenCourseRow, UserRow


class SqlUserRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def id_of(self, subject: str) -> UUID:
        by_subject = select(UserRow.id).where(UserRow.subject == subject)
        with DbSession(self._engine) as db:
            existing = db.execute(by_subject).scalar_one_or_none()
            if existing is not None:
                return existing
            inserted = insert(UserRow).values(id=uuid4(), subject=subject)
            user_id = db.execute(
                inserted.on_conflict_do_update(
                    index_elements=[UserRow.subject],
                    set_={"subject": inserted.excluded.subject},
                ).returning(UserRow.id)
            ).scalar_one()
            db.commit()
            return user_id

    def taken(self, user_id: UUID) -> frozenset[str]:
        with DbSession(self._engine) as db:
            return frozenset(
                db.scalars(select(TakenCourseRow.name).where(TakenCourseRow.user_id == user_id))
            )

    def add_taken(self, user_id: UUID, name: str) -> None:
        with DbSession(self._engine) as db, db.begin():
            db.execute(
                insert(TakenCourseRow).values(user_id=user_id, name=name).on_conflict_do_nothing()
            )

    def delete(self, user_id: UUID) -> None:
        with DbSession(self._engine) as db, db.begin():
            db.execute(delete(UserRow).where(UserRow.id == user_id))

    def remove_taken(self, user_id: UUID, name: str) -> None:
        with DbSession(self._engine) as db, db.begin():
            db.execute(
                delete(TakenCourseRow).where(
                    TakenCourseRow.user_id == user_id, TakenCourseRow.name == name
                )
            )
