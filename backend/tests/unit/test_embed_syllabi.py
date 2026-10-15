import pytest

from app.application.embed_syllabi import (
    EMBED_BATCH_SIZE,
    EmbedError,
    EmbedReport,
    EmbedSyllabi,
)
from app.domain.chunk import SyllabusChunk, chunks_of
from tests.builders import syllabus
from tests.fakes import FakeCourseRepository

MODEL = "fake-embedding"


class FakeEmbedder:
    model = MODEL

    def __init__(self, failing_call: int | None = None) -> None:
        self.calls: list[list[str]] = []
        self._failing_call = failing_call

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if len(self.calls) == self._failing_call:
            raise ConnectionError("API が応答しない")
        return [[float(len(text))] for text in texts]


class FakeChunkRepository:
    def __init__(
        self,
        embedded: dict[str, list[float]] | None = None,
        years_without_chunks: tuple[int, ...] = (),
    ) -> None:
        self.embedded = dict(embedded or {})
        self.saved: list[tuple[str, dict[str, list[float]]]] = []
        self.replaced: list[tuple[int, list[SyllabusChunk]]] = []
        self.pruned_for: list[str] = []
        self._years_without_chunks = list(years_without_chunks)

    def embedded_hashes(self, model: str, hashes: set[str]) -> set[str]:
        return hashes & set(self.embedded)

    def save_embeddings(self, model: str, vectors: dict[str, list[float]]) -> None:
        self.saved.append((model, vectors))

    def replace_chunks(self, year: int, chunks: list[SyllabusChunk]) -> None:
        self.replaced.append((year, chunks))

    def years_without_chunks(self) -> list[int]:
        return self._years_without_chunks

    def prune_embeddings(self, model: str) -> int:
        self.pruned_for.append(model)
        return 2


def test_only_chunks_without_an_embedding_are_sent_to_the_model() -> None:
    pages = (syllabus("10001"), syllabus("10002"))
    chunks = [chunk for page in pages for chunk in chunks_of(page)]
    store = FakeChunkRepository({chunks[0].content_hash: [0.0]})
    embedder = FakeEmbedder()

    report = EmbedSyllabi(FakeCourseRepository(syllabi=pages), store, embedder).run(2026)

    assert report == EmbedReport(chunks=6, texts=6, embedded=5, reused=1)
    assert embedder.calls == [[chunk.text for chunk in chunks[1:]]]
    assert store.saved == [
        (MODEL, {chunk.content_hash: [float(len(chunk.text))] for chunk in chunks[1:]})
    ]
    assert store.replaced == [(2026, chunks)]
    assert store.pruned_for == []


def test_identical_texts_are_embedded_once_and_counted_as_one_text() -> None:
    pages = (syllabus("10001"), syllabus("10001"))
    embedder = FakeEmbedder()

    report = EmbedSyllabi(FakeCourseRepository(syllabi=pages), FakeChunkRepository(), embedder).run(
        2026
    )

    assert report == EmbedReport(chunks=6, texts=3, embedded=3, reused=0)
    assert len(embedder.calls[0]) == 3


def test_each_batch_is_saved_before_the_next_so_a_failure_keeps_earlier_ones() -> None:
    pages = tuple(syllabus(f"{10000 + number}") for number in range(40))
    store = FakeChunkRepository()

    with pytest.raises(ConnectionError):
        EmbedSyllabi(FakeCourseRepository(syllabi=pages), store, FakeEmbedder(2)).run(2026)

    assert [len(vectors) for _, vectors in store.saved] == [EMBED_BATCH_SIZE]
    assert store.replaced == []


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


def test_prune_keeps_only_the_current_model() -> None:
    store = FakeChunkRepository()

    removed = EmbedSyllabi(FakeCourseRepository(), store, FakeEmbedder()).prune()

    assert removed == 2
    assert store.pruned_for == [MODEL]


def test_prune_refuses_while_a_year_has_syllabi_but_no_chunks() -> None:
    store = FakeChunkRepository(years_without_chunks=(2025, 2027))

    with pytest.raises(EmbedError, match="2025、2027 年度のシラバスにチャンクがありません"):
        EmbedSyllabi(FakeCourseRepository(), store, FakeEmbedder()).prune()
    assert store.pruned_for == []
