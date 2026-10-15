import pytest

from app.application.embed_syllabi import EmbedError, EmbedReport, EmbedSyllabi
from app.domain.chunk import SyllabusChunk, chunks_of
from tests.builders import syllabus
from tests.fakes import FakeCourseRepository

MODEL = "fake-embedding"


class FakeEmbedder:
    model = MODEL

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(len(text))] for text in texts]


class FakeChunkRepository:
    def __init__(self, embedded: dict[str, list[float]] | None = None) -> None:
        self.embedded = dict(embedded or {})
        self.saved: list[tuple[str, dict[str, list[float]]]] = []
        self.replaced: list[tuple[int, list[SyllabusChunk]]] = []
        self.prunes = 0

    def embedded_hashes(self, model: str, hashes: set[str]) -> set[str]:
        return hashes & set(self.embedded)

    def save_embeddings(self, model: str, vectors: dict[str, list[float]]) -> None:
        self.saved.append((model, vectors))

    def replace_chunks(self, year: int, chunks: list[SyllabusChunk]) -> None:
        self.replaced.append((year, chunks))

    def prune_embeddings(self) -> int:
        self.prunes += 1
        return 2


def test_only_chunks_without_an_embedding_are_sent_to_the_model() -> None:
    pages = (syllabus("10001"), syllabus("10002"))
    chunks = [chunk for page in pages for chunk in chunks_of(page)]
    already = chunks[0]
    store = FakeChunkRepository({already.content_hash: [0.0]})
    embedder = FakeEmbedder()

    report = EmbedSyllabi(FakeCourseRepository(syllabi=pages), store, embedder).run(2026)

    assert report == EmbedReport(chunks=6, embedded=5, reused=1, pruned=2)
    assert embedder.calls == [[chunk.text for chunk in chunks[1:]]]
    assert store.saved == [
        (MODEL, {chunk.content_hash: [float(len(chunk.text))] for chunk in chunks[1:]})
    ]
    assert store.replaced == [(2026, chunks)]
    assert store.prunes == 1


def test_nothing_is_sent_when_every_chunk_is_already_embedded() -> None:
    page = syllabus("10001")
    store = FakeChunkRepository({chunk.content_hash: [0.0] for chunk in chunks_of(page)})
    embedder = FakeEmbedder()

    report = EmbedSyllabi(FakeCourseRepository(syllabi=(page,)), store, embedder).run(2026)

    assert report.embedded == 0
    assert embedder.calls == []
    assert store.saved == []
    assert store.replaced == [(2026, chunks_of(page))]


def test_year_without_syllabi_is_an_error() -> None:
    store = FakeChunkRepository()

    with pytest.raises(EmbedError, match="2026 年度のシラバスが DB にありません"):
        EmbedSyllabi(FakeCourseRepository(), store, FakeEmbedder()).run(2026)
    assert store.replaced == []
