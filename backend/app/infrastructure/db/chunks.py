from sqlalchemy import Engine, delete, exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DbSession

from app.domain.chunk import SyllabusChunk
from app.infrastructure.db.models import EmbeddingRow, SyllabusChunkRow, SyllabusRow


class SqlChunkRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def embedded_hashes(self, model: str, hashes: set[str]) -> set[str]:
        if not hashes:
            return set()
        with DbSession(self._engine) as db:
            return set(
                db.scalars(
                    select(EmbeddingRow.content_hash).where(
                        EmbeddingRow.model == model, EmbeddingRow.content_hash.in_(hashes)
                    )
                )
            )

    def save_embeddings(self, model: str, vectors: dict[str, list[float]]) -> None:
        if not vectors:
            return
        with DbSession(self._engine) as db, db.begin():
            db.execute(
                insert(EmbeddingRow).on_conflict_do_nothing(),
                [
                    {"model": model, "content_hash": content_hash, "vector": vector}
                    for content_hash, vector in vectors.items()
                ],
            )

    def replace_chunks(self, year: int, chunks: list[SyllabusChunk]) -> None:
        with DbSession(self._engine) as db, db.begin():
            db.execute(delete(SyllabusChunkRow).where(SyllabusChunkRow.year == year))
            db.add_all(
                SyllabusChunkRow(
                    year=year,
                    syllabus_code=chunk.syllabus_code,
                    section=chunk.section.value,
                    text=chunk.text,
                    content_hash=chunk.content_hash,
                )
                for chunk in chunks
            )

    def years_without_chunks(self) -> list[int]:
        chunked = exists().where(SyllabusChunkRow.year == SyllabusRow.year)
        with DbSession(self._engine) as db:
            return list(
                db.scalars(
                    select(SyllabusRow.year).where(~chunked).distinct().order_by(SyllabusRow.year)
                )
            )

    def prune_embeddings(self, model: str) -> int:
        referenced = exists().where(SyllabusChunkRow.content_hash == EmbeddingRow.content_hash)
        with self._engine.begin() as connection:
            result = connection.execute(
                delete(EmbeddingRow).where(or_(EmbeddingRow.model != model, ~referenced))
            )
            return result.rowcount
