from dataclasses import dataclass

from app.application.ports import ChunkRepository, CourseRepository, Embedder
from app.domain.chunk import chunks_of


class EmbedError(ValueError):
    pass


@dataclass(frozen=True)
class EmbedReport:
    chunks: int
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
        if missing:
            vectors = self._embedder.embed([text_of[content_hash] for content_hash in missing])
            self._chunks.save_embeddings(
                self._embedder.model, dict(zip(missing, vectors, strict=True))
            )
        self._chunks.replace_chunks(year, chunks)
        return EmbedReport(len(chunks), len(missing), len(text_of) - len(missing))

    def prune(self) -> int:
        return self._chunks.prune_embeddings(self._embedder.model)
