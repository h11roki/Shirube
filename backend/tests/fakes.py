import json
from collections.abc import Set
from dataclasses import replace
from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.application.get_plan import GetPlan
from app.application.identify_user import IdentifyUser
from app.application.ports import EmbeddingError, InvalidTokenError
from app.application.request_plan import RequestPlan
from app.application.search_courses import SearchCourses
from app.domain.chunk import ChunkSection
from app.domain.course import CourseSection
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan, PlanStatus
from app.domain.ranking import ChunkHit
from app.domain.recommendation import CandidateCourse, CourseChoice
from app.domain.syllabus import Syllabus
from app.presentation.api.app import create_app
from tests.builders import course_section, syllabus

FAKE_MODEL = "fake-embedding"


class FakeEmbedder:
    model = FAKE_MODEL

    def __init__(self, failing_call: int | None = None) -> None:
        self.calls: list[list[str]] = []
        self._failing_call = failing_call

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if len(self.calls) == self._failing_call:
            raise EmbeddingError("埋め込みの API 呼び出しに失敗しました: 応答が無い")
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

    def syllabi_of(self, year: int, primary_codes: Set[str]) -> dict[str, Syllabus]:
        return {page.code: page for page in self.stored_syllabi if page.code in primary_codes}

    def syllabus_codes(self, year: int) -> dict[str, str]:
        return {
            code: page.code
            for page in self.stored_syllabi
            for code in (page.code, *(alias.code for alias in page.aliases))
        }


class FakePlanRepository:
    def __init__(self) -> None:
        self.plans: dict[UUID, Plan] = {}
        self.stall_limits: list[timedelta] = []

    def add(self, plan: Plan) -> None:
        self.plans[plan.id] = plan

    def claim_next(self) -> Plan | None:
        pending = [plan for plan in self.plans.values() if plan.status is PlanStatus.PENDING]
        return self.claim(pending[0].id) if pending else None

    def claim(self, plan_id: UUID) -> Plan | None:
        plan = self.plans.get(plan_id)
        if plan is None or plan.status is not PlanStatus.PENDING:
            return None
        self.plans[plan_id] = replace(plan, status=PlanStatus.RUNNING)
        return self.plans[plan_id]

    def finish(self, plan: Plan) -> bool:
        if self.plans[plan.id].status is not PlanStatus.RUNNING:
            return False
        self.plans[plan.id] = plan
        return True

    def fail_stalled(self, after: timedelta, failure: str) -> list[UUID]:
        self.stall_limits.append(after)
        running = [plan for plan in self.plans.values() if plan.status is PlanStatus.RUNNING]
        for plan in running:
            self.plans[plan.id] = plan.failed(failure)
        return [plan.id for plan in running]

    def get(self, plan_id: UUID) -> Plan | None:
        return self.plans.get(plan_id)

    def get_owned_by(self, plan_id: UUID, owner_id: UUID) -> Plan | None:
        plan = self.plans.get(plan_id)
        return plan if plan is not None and plan.owner_id == owner_id else None


TOKENS = {"token-a": "google-a", "token-b": "google-b"}


class FakeTokenVerifier:
    def __init__(self, subjects: dict[str, str]) -> None:
        self._subjects = subjects

    def subject_of(self, token: str) -> str:
        if token not in self._subjects:
            raise InvalidTokenError(f"知らない JWT です: {token}")
        return self._subjects[token]


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[str, UUID] = {}

    def id_of(self, subject: str) -> UUID:
        return self.users.setdefault(subject, uuid4())


def chat_answering(
    message: dict[str, Any],
    requests: list[dict[str, Any]] | None = None,
    finish_reason: str = "stop",
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
                        "finish_reason": finish_reason,
                        "message": {"role": "assistant", **message},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    return ChatOpenAI(model="test-model", api_key=SecretStr("test-key"), http_client=client)


def courses_ranked_by(
    similarities: dict[str, float],
) -> tuple[FakeCourseRepository, SearchCourses]:
    codes = [f"{10000 + number}" for number in range(len(similarities))]
    repository = FakeCourseRepository(
        sections=tuple(
            replace(course_section(code), name=name)
            for code, name in zip(codes, similarities, strict=True)
        ),
        syllabi=tuple(syllabus(code) for code in codes),
    )
    hits = [
        ChunkHit(code, ChunkSection.OVERVIEW, similarity)
        for code, similarity in zip(codes, similarities.values(), strict=True)
    ]
    return repository, SearchCourses(repository, FakeChunkSearch(hits), FakeEmbedder())


def failing_http_client(status: int) -> httpx.Client:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status, json={"error": {"message": "失敗", "type": "invalid_request_error"}}
        )

    return httpx.Client(transport=httpx.MockTransport(respond))


def chat_failing(status: int) -> ChatOpenAI:
    return ChatOpenAI(
        model="test-model", api_key=SecretStr("test-key"), http_client=failing_http_client(status)
    )


def plan_api(
    courses_and_search: tuple[FakeCourseRepository, SearchCourses] | None = None,
    plans: FakePlanRepository | None = None,
    users: FakeUserRepository | None = None,
    token: str | None = "token-a",
    today: date = date(2026, 10, 16),
) -> TestClient:
    courses, search = courses_and_search or courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    stored = plans or FakePlanRepository()
    identify = IdentifyUser(FakeTokenVerifier(TOKENS), users or FakeUserRepository())
    app = create_app(
        RequestPlan(search, courses, stored, 16), GetPlan(stored), identify, 2026, lambda: today
    )
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return TestClient(app, raise_server_exceptions=False, headers=headers)
