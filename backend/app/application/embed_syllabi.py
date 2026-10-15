from dataclasses import dataclass

from app.application.ports import ChunkRepository, CourseRepository, Embedder
from app.domain.chunk import chunks_of

EMBED_BATCH_SIZE = 100


class EmbedError(ValueError):
    pass


@dataclass(frozen=True)
class EmbedReport:
    chunks: int
    texts: int
    embedded: int
    reused: int


class EmbedSyllabi:
    def __init__(
        self, courses: CourseRepository, chunks: ChunkRepository, embedder: Embedder
    ) -> None:
        self._courses = courses
        self._chunks = chunks
        self._embedder = embedder

    def run(self, year: int) -> EmbedReport:
        syllabi = self._courses.syllabi(year)
        if not syllabi:
            raise EmbedError(f"{year} 年度のシラバスが DB にありません")
        chunks = [chunk for syllabus in syllabi for chunk in chunks_of(syllabus)]
        text_of = {chunk.content_hash: chunk.text for chunk in chunks}
        known = self._chunks.embedded_hashes(self._embedder.model, set(text_of))
        missing = [content_hash for content_hash in text_of if content_hash not in known]
        for start in range(0, len(missing), EMBED_BATCH_SIZE):
            batch = missing[start : start + EMBED_BATCH_SIZE]
            vectors = self._embedder.embed([text_of[content_hash] for content_hash in batch])
            self._chunks.save_embeddings(
                self._embedder.model, dict(zip(batch, vectors, strict=True))
            )
        self._chunks.replace_chunks(year, chunks)
        return EmbedReport(len(chunks), len(text_of), len(missing), len(text_of) - len(missing))

    def prune(self) -> int:
        unembedded = self._chunks.years_without_chunks()
        if unembedded:
            years = "、".join(str(year) for year in unembedded)
            raise EmbedError(f"{years} 年度のシラバスにチャンクがありません")
        return self._chunks.prune_embeddings(self._embedder.model)
