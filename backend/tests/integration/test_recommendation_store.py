from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, select

from app.application.ports import RecommendationKey
from app.domain.course import Term
from app.domain.recommendation import Recommendation
from app.domain.roadmap import Semester
from app.infrastructure.db.models import RememberedRecommendationRow
from app.infrastructure.db.recommendations import REMEMBERED_JSON_VERSION, SqlRecommendationStore
from tests.builders import sample_plan

NOON = datetime(2026, 11, 5, 12, tzinfo=UTC)
KEY = RecommendationKey(
    "職業", "情", 2026, (Semester(3, Term.SPRING), Semester(3, Term.AUTUMN)), ("10001",), "f1"
)


@pytest.fixture
def store(engine: Engine) -> Iterator[SqlRecommendationStore]:
    yield SqlRecommendationStore(engine)
    with engine.begin() as connection:
        connection.execute(delete(RememberedRecommendationRow))


def recommendation() -> Recommendation:
    result = sample_plan(uuid4()).result
    assert result is not None
    return result.recommendation


def test_a_remembered_recommendation_comes_back_for_the_same_key_until_it_expires(
    engine: Engine, store: SqlRecommendationStore
) -> None:
    store.remember(KEY, recommendation(), NOON + timedelta(days=7))

    assert store.recall(KEY, NOON) == recommendation()
    assert store.recall(KEY, NOON + timedelta(days=7)) is None
    with engine.connect() as connection:
        row = connection.execute(select(RememberedRecommendationRow)).one()
    assert (row.key, row.recommendation["version"]) == (KEY.digest, REMEMBERED_JSON_VERSION)


def test_another_key_does_not_match(store: SqlRecommendationStore) -> None:
    store.remember(KEY, recommendation(), NOON + timedelta(days=7))

    other = RecommendationKey(KEY.occupation, KEY.department, KEY.year, KEY.semesters, (), "f1")
    assert store.recall(other, NOON) is None


def test_remembering_the_same_key_again_replaces_the_recommendation_and_its_expiry(
    store: SqlRecommendationStore,
) -> None:
    store.remember(KEY, recommendation(), NOON + timedelta(days=1))

    store.remember(KEY, recommendation(), NOON + timedelta(days=7))

    assert store.recall(KEY, NOON + timedelta(days=2)) == recommendation()


def test_forgetting_removes_only_what_has_expired(store: SqlRecommendationStore) -> None:
    fresh = RecommendationKey("別の職業", "情", 2026, KEY.semesters, (), "f1")
    store.remember(KEY, recommendation(), NOON + timedelta(hours=1))
    store.remember(fresh, recommendation(), NOON + timedelta(days=7))

    assert store.forget_expired(NOON + timedelta(hours=1)) == 1
    assert store.recall(KEY, NOON) is None
    assert store.recall(fresh, NOON) == recommendation()
    assert store.forget_expired(NOON + timedelta(hours=1)) == 0


def test_forgetting_everything_empties_the_store_for_replaced_course_data(
    store: SqlRecommendationStore,
) -> None:
    store.remember(KEY, recommendation(), NOON + timedelta(days=7))

    assert store.forget_all() == 1
    assert store.recall(KEY, NOON) is None
    assert store.forget_all() == 0
