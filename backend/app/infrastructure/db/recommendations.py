from datetime import datetime

from sqlalchemy import Engine, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DbSession

from app.application.ports import RecommendationKey
from app.domain.recommendation import Recommendation
from app.infrastructure.db.models import RememberedJson, RememberedRecommendationRow
from app.infrastructure.db.plans import recommendation_from_json, recommendation_json, semester_json

REMEMBERED_JSON_VERSION = 1


class SqlRecommendationStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def recall(self, key: RecommendationKey, now: datetime) -> Recommendation | None:
        with DbSession(self._engine) as db:
            row = db.get(RememberedRecommendationRow, key.digest)
            if (
                row is None
                or row.expires_at <= now
                or row.recommendation["version"] != REMEMBERED_JSON_VERSION
            ):
                return None
            return recommendation_from_json(row.recommendation["recommendation"])

    def remember(
        self, key: RecommendationKey, recommendation: Recommendation, until: datetime
    ) -> None:
        stored = RememberedJson(
            version=REMEMBERED_JSON_VERSION, recommendation=recommendation_json(recommendation)
        )
        statement = insert(RememberedRecommendationRow).values(
            key=key.digest,
            occupation=key.occupation,
            department=key.department,
            year=key.year,
            semesters=[semester_json(semester) for semester in key.semesters],
            excluded=list(key.excluded),
            fingerprint=key.fingerprint,
            recommendation=stored,
            expires_at=until,
        )
        with DbSession(self._engine) as db, db.begin():
            db.execute(
                statement.on_conflict_do_update(
                    index_elements=[RememberedRecommendationRow.key],
                    set_={
                        "recommendation": statement.excluded.recommendation,
                        "expires_at": statement.excluded.expires_at,
                        "created_at": func.now(),
                    },
                )
            )

    def forget_expired(self, now: datetime) -> int:
        with DbSession(self._engine) as db, db.begin():
            forgotten = db.connection().execute(
                delete(RememberedRecommendationRow).where(
                    RememberedRecommendationRow.expires_at <= now
                )
            )
            return forgotten.rowcount

    def forget_all(self) -> int:
        with DbSession(self._engine) as db, db.begin():
            forgotten = db.connection().execute(delete(RememberedRecommendationRow))
            return forgotten.rowcount
