from sqlalchemy import Engine, Text, any_, bindparam, delete, exists, or_, select, union
from sqlalchemy.dialects.postgresql import ARRAY, insert
from sqlalchemy.orm import Session as DbSession

from app.domain.chunk import SyllabusChunk
from app.infrastructure.db.models import EmbeddingRow, SyllabusChunkRow, SyllabusRow


class SqlChunkRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def embedded_hashes(self, model: str, hashes: set[str]) -> set[str]:
        if not hashes:
            return set()
        wanted = bindparam("hashes", sorted(hashes), type_=ARRAY(Text()))
        with DbSession(self._engine) as db:
            return set(
                db.scalars(
                    select(EmbeddingRow.content_hash).where(
                        EmbeddingRow.model == model, EmbeddingRow.content_hash == any_(wanted)
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
            if chunks:
                db.execute(
                    insert(SyllabusChunkRow),
                    [
                        {
                            "year": year,
                            "syllabus_code": chunk.syllabus_code,
                            "section": chunk.section.value,
                            "text": chunk.text,
                            "content_hash": chunk.content_hash,
                        }
                        for chunk in chunks
                    ],
                )

    def years_not_embedded(self, model: str) -> list[int]:
        chunked = exists().where(SyllabusChunkRow.year == SyllabusRow.year)
        embedded = exists().where(
            EmbeddingRow.model == model, EmbeddingRow.content_hash == SyllabusChunkRow.content_hash
        )
        years = union(
            select(SyllabusRow.year).where(~chunked),
            select(SyllabusChunkRow.year).where(~embedded),
        ).subquery()
        with DbSession(self._engine) as db:
            return list(db.scalars(select(years.c.year).order_by(years.c.year)))

    def prune_embeddings(self, model: str) -> int:
        referenced = exists().where(SyllabusChunkRow.content_hash == EmbeddingRow.content_hash)
        with DbSession(self._engine) as db, db.begin():
            result = db.connection().execute(
                delete(EmbeddingRow).where(or_(EmbeddingRow.model != model, ~referenced))
            )
            return result.rowcount
