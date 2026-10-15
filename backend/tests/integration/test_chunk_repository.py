from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, delete, select

from app.domain.chunk import ChunkSection, SyllabusChunk, chunks_of
from app.infrastructure.db.chunks import SqlChunkRepository
from app.infrastructure.db.courses import SqlCourseRepository
from app.infrastructure.db.models import EMBEDDING_DIMENSIONS, EmbeddingRow, SyllabusChunkRow
from tests.builders import syllabus

YEAR = 2098
MODEL = "test-embedding"
OLD_MODEL = "test-embedding-old"


def vector(seed: float) -> list[float]:
    return [seed] * EMBEDDING_DIMENSIONS


@pytest.fixture
def stores(engine: Engine) -> Iterator[tuple[SqlCourseRepository, SqlChunkRepository]]:
    courses = SqlCourseRepository(engine)
    chunks = SqlChunkRepository(engine)
    courses.replace_syllabi(YEAR, [syllabus("10001", year=YEAR), syllabus("10002", year=YEAR)])
    yield courses, chunks
    courses.replace_syllabi(YEAR, [])
    with engine.begin() as connection:
        connection.execute(delete(EmbeddingRow))


def test_saved_embeddings_are_found_by_model_and_hash(
    engine: Engine, stores: tuple[SqlCourseRepository, SqlChunkRepository]
) -> None:
    _, chunks = stores

    chunks.save_embeddings(MODEL, {"a" * 64: vector(0.5)})
    chunks.save_embeddings(MODEL, {"a" * 64: vector(0.9)})

    assert chunks.embedded_hashes(MODEL, {"a" * 64, "b" * 64}) == {"a" * 64}
    assert chunks.embedded_hashes("other-model", {"a" * 64}) == set()
    assert chunks.embedded_hashes(MODEL, set()) == set()
    with engine.connect() as connection:
        stored = connection.scalar(select(EmbeddingRow.vector).where(EmbeddingRow.model == MODEL))
    assert stored is not None
    assert list(stored) == pytest.approx(vector(0.5))


def test_chunks_are_replaced_per_year_and_follow_their_syllabus(
    engine: Engine, stores: tuple[SqlCourseRepository, SqlChunkRepository]
) -> None:
    courses, chunks = stores
    first = chunks_of(syllabus("10001", year=YEAR))

    chunks.replace_chunks(YEAR, first)
    chunks.replace_chunks(YEAR, first[:1])

    with engine.connect() as connection:
        rows = connection.execute(
            select(SyllabusChunkRow.syllabus_code, SyllabusChunkRow.section).where(
                SyllabusChunkRow.year == YEAR
            )
        ).all()
    assert rows == [("10001", ChunkSection.OVERVIEW.value)]

    courses.replace_syllabi(YEAR, [syllabus("10002", year=YEAR)])

    with engine.connect() as connection:
        remaining = connection.scalars(
            select(SyllabusChunkRow.syllabus_code).where(SyllabusChunkRow.year == YEAR)
        ).all()
    assert remaining == []


def test_prune_removes_other_models_and_embeddings_no_chunk_refers_to(
    stores: tuple[SqlCourseRepository, SqlChunkRepository],
) -> None:
    _, chunks = stores
    kept = SyllabusChunk("10001", ChunkSection.OVERVIEW, "残る本文")
    chunks.replace_chunks(YEAR, [kept])
    chunks.save_embeddings(MODEL, {kept.content_hash: vector(0.1), "c" * 64: vector(0.2)})
    chunks.save_embeddings(OLD_MODEL, {kept.content_hash: vector(0.3)})

    removed = chunks.prune_embeddings(MODEL)

    assert removed == 2
    assert chunks.embedded_hashes(MODEL, {kept.content_hash, "c" * 64}) == {kept.content_hash}
    assert chunks.embedded_hashes(OLD_MODEL, {kept.content_hash}) == set()
