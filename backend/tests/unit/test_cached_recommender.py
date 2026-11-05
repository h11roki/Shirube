import logging
from datetime import UTC, datetime, timedelta

import pytest

from app.application.cached_recommender import CachedRecommender
from app.application.ports import RecommendationKey
from app.application.recommend_courses import RecommendStep
from app.domain.course import Term
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import Recommendation, RecommendedCourse, Relevance
from app.domain.roadmap import Semester
from tests.fakes import FakeRecommendationStore, FakeRecommender

PROFILE = OccupationProfile("職業", "解釈した職業", None, ("甲", "乙", "丙"))
RECOMMENDATION = Recommendation(
    PROFILE, (RecommendedCourse("科目A", "10000", Relevance.CORE, "理由A"),), ("科目A", "科目B")
)
SEMESTERS = (Semester(3, Term.SPRING), Semester(3, Term.AUTUMN))
NOON = datetime(2026, 11, 5, 12, tzinfo=UTC)
WEEK = timedelta(days=7)


def cached(
    store: FakeRecommendationStore | None = None,
    fingerprint: str = "f1",
    now: datetime = NOON,
) -> tuple[CachedRecommender, FakeRecommender, FakeRecommendationStore]:
    inner = FakeRecommender(RECOMMENDATION)
    kept = store or FakeRecommendationStore()
    return CachedRecommender(inner, kept, fingerprint, WEEK, lambda: now), inner, kept


def test_a_recommendation_not_remembered_is_made_and_kept_for_the_lifetime() -> None:
    recommender, inner, store = cached()
    steps: list[RecommendStep] = []

    made = recommender.run("職業", 2026, "情", SEMESTERS, steps.append, {"科目B"})

    assert made == RECOMMENDATION
    assert inner.calls == [("職業", 2026, "情", SEMESTERS, frozenset({"科目B"}))]
    assert steps == [RecommendStep.SEARCHING, RecommendStep.SELECTING]
    [(key, kept, until)] = store.remembered.values()
    assert key == RecommendationKey("職業", "情", 2026, SEMESTERS, ("科目B",), "f1")
    assert (kept, until) == (RECOMMENDATION, NOON + WEEK)


def test_a_remembered_recommendation_is_used_without_the_recommender_or_its_steps(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store = FakeRecommendationStore()
    first, _, _ = cached(store)
    first.run("職業", 2026, "情", SEMESTERS, excluded={"科目B", "科目C"})
    recommender, inner, _ = cached(store, now=NOON + timedelta(days=6))
    steps: list[RecommendStep] = []

    with caplog.at_level(logging.INFO):
        again = recommender.run("職業", 2026, "情", SEMESTERS, steps.append, {"科目C", "科目B"})

    assert again == RECOMMENDATION
    assert inner.calls == []
    assert steps == []
    assert "残した推薦を使います" in caplog.text


def test_an_expired_recommendation_is_made_again() -> None:
    store = FakeRecommendationStore()
    first, _, _ = cached(store)
    first.run("職業", 2026, "情", SEMESTERS)
    recommender, inner, _ = cached(store, now=NOON + WEEK)

    recommender.run("職業", 2026, "情", SEMESTERS)

    assert len(inner.calls) == 1


@pytest.mark.parametrize(
    "occupation, department, year, semesters, excluded, fingerprint",
    [
        ("職業 ", "情", 2026, SEMESTERS, (), "f1"),
        ("職業", "機", 2026, SEMESTERS, (), "f1"),
        ("職業", "情", 2027, SEMESTERS, (), "f1"),
        ("職業", "情", 2026, SEMESTERS[:1], (), "f1"),
        ("職業", "情", 2026, SEMESTERS, ("科目B",), "f1"),
        ("職業", "情", 2026, SEMESTERS, (), "f2"),
    ],
)
def test_every_part_of_the_key_tells_recommendations_apart(
    occupation: str,
    department: str,
    year: int,
    semesters: tuple[Semester, ...],
    excluded: tuple[str, ...],
    fingerprint: str,
) -> None:
    base = RecommendationKey("職業", "情", 2026, SEMESTERS, (), "f1")
    other = RecommendationKey(occupation, department, year, semesters, excluded, fingerprint)

    assert base.digest == RecommendationKey("職業", "情", 2026, SEMESTERS, (), "f1").digest
    assert base.digest != other.digest


def test_a_store_that_cannot_be_read_or_written_does_not_stop_the_plan(
    caplog: pytest.LogCaptureFixture,
) -> None:
    recommender, inner, _ = cached(FakeRecommendationStore(failing=True))

    with caplog.at_level(logging.ERROR):
        made = recommender.run("職業", 2026, "情", SEMESTERS)

    assert made == RECOMMENDATION
    assert len(inner.calls) == 1
    assert "読めなかった" in caplog.text
    assert "残せませんでした" in caplog.text


def test_a_lifetime_that_is_not_positive_is_refused() -> None:
    with pytest.raises(ValueError, match="正にしてください"):
        CachedRecommender(
            FakeRecommender(RECOMMENDATION),
            FakeRecommendationStore(),
            "f1",
            timedelta(0),
            lambda: NOON,
        )
