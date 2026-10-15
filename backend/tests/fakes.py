from app.domain.course import CourseSection
from app.domain.ranking import ChunkHit
from app.domain.syllabus import Syllabus

FAKE_MODEL = "fake-embedding"


class FakeEmbedder:
    model = FAKE_MODEL

    def __init__(self, failing_call: int | None = None) -> None:
        self.calls: list[list[str]] = []
        self._failing_call = failing_call

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if len(self.calls) == self._failing_call:
            raise ConnectionError("API が応答しない")
        return [[float(len(text))] for text in texts]


class FakeChunkSearch:
    def __init__(
        self,
        hits: list[ChunkHit],
        hits_by_vector: dict[float, list[ChunkHit]] | None = None,
        embedded: bool = True,
    ) -> None:
        self._hits = hits
        self._hits_by_vector = hits_by_vector or {}
        self._embedded = embedded
        self.calls: list[tuple[int, str, list[float], set[str]]] = []

    def is_embedded(self, year: int, model: str) -> bool:
        return self._embedded

    def best_chunks(
        self, year: int, model: str, vector: list[float], syllabus_codes: set[str]
    ) -> list[ChunkHit]:
        self.calls.append((year, model, vector, syllabus_codes))
        hits = self._hits_by_vector.get(vector[0], self._hits)
        return [hit for hit in hits if hit.syllabus_code in syllabus_codes]


class FakeCourseRepository:
    def __init__(
        self, sections: tuple[CourseSection, ...] = (), syllabi: tuple[Syllabus, ...] = ()
    ) -> None:
        self.stored_sections = list(sections)
        self.stored_syllabi = list(syllabi)
        self.section_calls: list[tuple[int, list[CourseSection]]] = []
        self.syllabus_calls: list[tuple[int, list[Syllabus]]] = []

    def replace_sections(self, year: int, sections: list[CourseSection]) -> None:
        self.section_calls.append((year, sections))

    def replace_syllabi(self, year: int, syllabi: list[Syllabus]) -> None:
        self.syllabus_calls.append((year, syllabi))

    def sections(self, year: int) -> list[CourseSection]:
        return self.stored_sections

    def syllabi(self, year: int) -> list[Syllabus]:
        return self.stored_syllabi

    def syllabus(self, year: int, code: str) -> Syllabus | None:
        return next((page for page in self.stored_syllabi if page.code == code), None)

    def syllabus_codes(self, year: int) -> dict[str, str]:
        return {
            code: page.code
            for page in self.stored_syllabi
            for code in (page.code, *(alias.code for alias in page.aliases))
        }
