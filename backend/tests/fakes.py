import json
from collections.abc import Set
from typing import Any

import httpx
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.domain.course import CourseSection
from app.domain.occupation import OccupationProfile
from app.domain.ranking import ChunkHit
from app.domain.recommendation import CandidateCourse, CourseChoice
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


class FakeOccupationAnalyzer:
    def __init__(self, profiles: dict[str, OccupationProfile]) -> None:
        self._profiles = profiles
        self.calls: list[str] = []

    def analyze(self, occupation: str) -> OccupationProfile:
        self.calls.append(occupation)
        return self._profiles[occupation]


class FakeCourseSelector:
    def __init__(self, choices: list[CourseChoice]) -> None:
        self._choices = choices
        self.calls: list[tuple[OccupationProfile, list[CandidateCourse]]] = []

    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        self.calls.append((profile, candidates))
        return self._choices


class FakeChunkSearch:
    def __init__(
        self,
        hits: list[ChunkHit],
        hits_by_length: dict[float, list[ChunkHit]] | None = None,
        embedded: bool = True,
    ) -> None:
        self._hits = hits
        self._hits_by_length = hits_by_length or {}
        self._embedded = embedded
        self.calls: list[tuple[int, str, list[float], set[str]]] = []

    def is_embedded(self, year: int, model: str) -> bool:
        return self._embedded

    def best_chunks(
        self, year: int, model: str, vector: list[float], syllabus_codes: set[str]
    ) -> list[ChunkHit]:
        self.calls.append((year, model, vector, syllabus_codes))
        hits = self._hits_by_length.get(vector[0], self._hits)
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

    def syllabi_of(self, year: int, codes: Set[str]) -> dict[str, Syllabus]:
        return {page.code: page for page in self.stored_syllabi if page.code in codes}

    def syllabus_codes(self, year: int) -> dict[str, str]:
        return {
            code: page.code
            for page in self.stored_syllabi
            for code in (page.code, *(alias.code for alias in page.aliases))
        }


def chat_answering(
    message: dict[str, Any], requests: list[dict[str, Any]] | None = None
) -> ChatOpenAI:
    def respond(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", **message},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    return ChatOpenAI(model="test-model", api_key=SecretStr("test-key"), http_client=client)
