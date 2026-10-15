from sqlalchemy import Engine, delete, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DbSession

from app.domain.chunk import SyllabusChunk
from app.infrastructure.db.models import EmbeddingRow, SyllabusChunkRow


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

    def prune_embeddings(self) -> int:
        referenced = exists().where(SyllabusChunkRow.content_hash == EmbeddingRow.content_hash)
        with DbSession(self._engine) as db, db.begin():
            removed = db.scalars(
                delete(EmbeddingRow)
                .where(~referenced)
                .returning(EmbeddingRow.content_hash)
                .execution_options(synchronize_session=False)
            )
            return len(removed.all())
