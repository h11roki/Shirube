import json
from collections.abc import Callable, Iterator, Sequence, Set
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.application.answer_taken_courses import AnswerTakenCourses
from app.application.check_health import CheckHealth
from app.application.delete_account import DeleteAccount
from app.application.delete_plan import DeletePlan
from app.application.get_plan import GetPlan
from app.application.identify_user import IdentifyUser
from app.application.list_class_choices import ListClassChoices
from app.application.list_offered_courses import ListOfferedCourses
from app.application.list_plans import ListPlans
from app.application.ports import (
    Deletion,
    EmbeddingError,
    InvalidTokenError,
    PlanBuild,
    PlanRepository,
    RecommendationKey,
    RecordedBuild,
    StorageUnavailableError,
    TokenUsage,
)
from app.application.recommend_courses import RecommendStep
from app.application.request_plan import RequestPlan
from app.application.search_courses import SearchCourses, query_and_skills
from app.application.syllabus_links import SyllabusLinks
from app.application.taken_courses import TakenCourses
from app.domain.chunk import ChunkSection
from app.domain.course import CourseSection
from app.domain.occupation import OccupationProfile
from app.domain.plan import (
    IN_PROGRESS,
    Plan,
    PlanListing,
    PlanResult,
    PlanStage,
    PlanStatus,
    PlanSummary,
)
from app.domain.quota import PlanCounts, PlanQuota
from app.domain.ranking import ChunkHit
from app.domain.recommendation import CandidateCourse, CourseChoice, Recommendation
from app.domain.roadmap import Semester
from app.domain.syllabus import Syllabus
from app.presentation.api.app import create_app
from tests.builders import course_section, sample_conditions, syllabus

FAKE_MODEL = "fake-embedding"
FIRST_CREATED_AT = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)
API_VERSION = "0123abc"
QUOTA = PlanQuota(3, 30)


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

    def syllabus_urls(self, year: int, primary_codes: Set[str]) -> dict[str, str]:
        return {
            page.code: page.url
            for page in self.stored_syllabi
            if page.year == year and page.code in primary_codes and page.url is not None
        }


class Ticks:
    def __init__(self) -> None:
        self.now = -1.0

    def __call__(self) -> float:
        self.now += 1.0
        return self.now


class FakeUsageMeter:
    def __init__(self, usage: dict[str, TokenUsage] | None = None) -> None:
        self.usage = usage or {}

    @contextmanager
    def meter(self) -> Iterator[Callable[[], dict[str, TokenUsage]]]:
        yield lambda: self.usage


class FakePlanBuildLog:
    def __init__(self, recorded: Sequence[RecordedBuild] = ()) -> None:
        self.builds: list[tuple[UUID, PlanBuild]] = []
        self.recorded = list(recorded)
        self.starts: list[datetime] = []

    def record(self, plan_id: UUID, build: PlanBuild) -> None:
        self.builds.append((plan_id, build))

    def since(self, start: datetime) -> list[RecordedBuild]:
        self.starts.append(start)
        return [recorded for recorded in self.recorded if recorded.finished_at >= start]


class FakeRecommendationStore:
    def __init__(self, failing: bool = False) -> None:
        self.remembered: dict[str, tuple[RecommendationKey, Recommendation, datetime]] = {}
        self.forgets: list[datetime] = []
        self._failing = failing

    def recall(self, key: RecommendationKey, now: datetime) -> Recommendation | None:
        if self._failing:
            raise ConnectionError("DB に届きません")
        entry = self.remembered.get(key.digest)
        if entry is None:
            return None
        _, recommendation, until = entry
        return recommendation if until > now else None

    def remember(
        self, key: RecommendationKey, recommendation: Recommendation, until: datetime
    ) -> None:
        if self._failing:
            raise ConnectionError("DB に届きません")
        self.remembered[key.digest] = (key, recommendation, until)

    def forget_expired(self, now: datetime) -> int:
        if self._failing:
            raise ConnectionError("DB に届きません")
        self.forgets.append(now)
        expired = [digest for digest, (_, _, until) in self.remembered.items() if until <= now]
        for digest in expired:
            del self.remembered[digest]
        return len(expired)

    def forget_all(self) -> int:
        if self._failing:
            raise ConnectionError("DB に届きません")
        forgotten = len(self.remembered)
        self.remembered.clear()
        return forgotten


class FakeRecommender:
    def __init__(self, recommendation: Recommendation) -> None:
        self._recommendation = recommendation
        self.calls: list[tuple[str, int, str, tuple[Semester, ...], frozenset[str]]] = []

    def run(
        self,
        occupation: str,
        year: int,
        department: str,
        semesters: Sequence[Semester],
        enter: Callable[[RecommendStep, OccupationProfile], None] = lambda step, profile: None,
        excluded: Set[str] = frozenset(),
    ) -> Recommendation:
        self.calls.append((occupation, year, department, tuple(semesters), frozenset(excluded)))
        enter(RecommendStep.SEARCHING, self._recommendation.profile)
        enter(RecommendStep.SELECTING, self._recommendation.profile)
        return self._recommendation


class FakePlanRepository:
    def __init__(self) -> None:
        self.plans: dict[UUID, Plan] = {}
        self.deleted: dict[UUID, UUID | None] = {}
        self.purges: list[datetime] = []
        self.created_at: dict[UUID, datetime] = {}
        self.stall_limits: list[timedelta] = []
        self.stages: list[tuple[UUID, PlanStage, OccupationProfile]] = []

    def store(self, plan: Plan) -> None:
        self.plans[plan.id] = plan
        self.created_at[plan.id] = FIRST_CREATED_AT + timedelta(minutes=len(self.created_at))

    def add(self, plan: Plan, since: datetime, admit: Callable[[PlanCounts], None]) -> None:
        mine = [stored for stored in self.plans.values() if stored.owner_id == plan.owner_id]
        today = [stored for stored in self.plans.values() if self.created_at[stored.id] >= since]
        deleted_today = [
            owner for plan_id, owner in self.deleted.items() if self.created_at[plan_id] >= since
        ]
        admit(
            PlanCounts(
                sum(stored.status in IN_PROGRESS for stored in mine),
                sum(
                    stored.owner_id == plan.owner_id and stored.status is not PlanStatus.FAILED
                    for stored in today
                )
                + deleted_today.count(plan.owner_id),
                len(today) + len(deleted_today),
            )
        )
        self.store(plan)

    def delete_owned_by(self, plan_id: UUID, owner_id: UUID, since: datetime) -> Deletion:
        plan = self.plans.get(plan_id)
        if plan is None or plan.owner_id != owner_id:
            return Deletion.MISSING
        if plan.status is PlanStatus.RUNNING:
            return Deletion.RUNNING
        del self.plans[plan_id]
        if self.created_at[plan_id] >= since:
            self.deleted[plan_id] = None if plan.status is PlanStatus.FAILED else owner_id
        return Deletion.DELETED

    def purge_deleted(self, before: datetime) -> int:
        self.purges.append(before)
        purged = [plan_id for plan_id in self.deleted if self.created_at[plan_id] < before]
        for plan_id in purged:
            del self.deleted[plan_id]
        return len(purged)

    def list_owned_by(self, owner_id: UUID, limit: int) -> PlanListing:
        owned = sorted(
            (plan for plan in self.plans.values() if plan.owner_id == owner_id),
            key=lambda plan: self.created_at[plan.id],
            reverse=True,
        )
        return PlanListing(
            [
                PlanSummary(
                    plan.id,
                    plan.status,
                    plan.conditions.occupation,
                    plan.conditions.start,
                    self.created_at[plan.id],
                )
                for plan in owned[:limit]
            ],
            len(owned),
        )

    def claim_next(self) -> Plan | None:
        pending = [plan for plan in self.plans.values() if plan.status is PlanStatus.PENDING]
        return self.claim(pending[0].id) if pending else None

    def oldest_waiting(self) -> datetime | None:
        return min(
            (
                self.created_at[plan.id]
                for plan in self.plans.values()
                if plan.status is PlanStatus.PENDING
            ),
            default=None,
        )

    def claim(self, plan_id: UUID) -> Plan | None:
        plan = self.plans.get(plan_id)
        if plan is None or plan.status is not PlanStatus.PENDING:
            return None
        self.plans[plan_id] = replace(plan, status=PlanStatus.RUNNING, stage=PlanStage.ANALYZING)
        return self.plans[plan_id]

    def enter_stage(self, plan: Plan) -> None:
        stored = self.plans.get(plan.id)
        if stored is not None and stored.status is PlanStatus.RUNNING:
            assert plan.stage is not None and plan.reading is not None
            self.stages.append((plan.id, plan.stage, plan.reading))
            self.plans[plan.id] = replace(stored, stage=plan.stage, reading=plan.reading)

    def finish(self, plan: Plan) -> bool:
        stored = self.plans.get(plan.id)
        if stored is None or stored.status is not PlanStatus.RUNNING:
            return False
        self.plans[plan.id] = plan
        return True

    def replace_result(self, plan: Plan, previous: PlanResult) -> bool:
        stored = self.plans[plan.id]
        if stored.status is not PlanStatus.SUCCEEDED or stored.result != previous:
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
        self.remembered: dict[UUID, set[str]] = {}
        self.building: set[UUID] = set()

    def id_of(self, subject: str) -> UUID:
        return self.users.setdefault(subject, uuid4())

    def taken(self, user_id: UUID) -> frozenset[str]:
        return frozenset(self.remembered.get(user_id, set()))

    def add_taken(self, user_id: UUID, name: str) -> None:
        self.remembered.setdefault(user_id, set()).add(name)

    def remove_taken(self, user_id: UUID, name: str) -> None:
        self.remembered.setdefault(user_id, set()).discard(name)

    def delete(self, user_id: UUID, since: datetime) -> Deletion:
        if user_id in self.building:
            return Deletion.RUNNING
        self.users = {subject: known for subject, known in self.users.items() if known != user_id}
        self.remembered.pop(user_id, None)
        return Deletion.DELETED


def chat_answering(
    message: dict[str, Any],
    requests: list[dict[str, Any]] | None = None,
    finish_reason: str = "stop",
    then: Sequence[dict[str, Any]] = (),
) -> ChatOpenAI:
    answers = [message, *then]
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if requests is not None:
            requests.append(json.loads(request.content))
        reply = answers[min(calls, len(answers)) - 1]
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
                        "message": {"role": "assistant", **reply},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    return ChatOpenAI(model="test-model", api_key=SecretStr("test-key"), http_client=client)


def courses_ranked_by(
    similarities: dict[str, float], embedder: FakeEmbedder | None = None
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
    return repository, SearchCourses(
        repository, FakeChunkSearch(hits), embedder or FakeEmbedder(), query_and_skills
    )


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


STALL_AFTER = timedelta(hours=1)


class UnreachablePlans(FakePlanRepository):
    def oldest_waiting(self) -> datetime | None:
        raise StorageUnavailableError("DB に繋がらない")


def queued(waited: timedelta, status: PlanStatus = PlanStatus.PENDING) -> FakePlanRepository:
    plans = FakePlanRepository()
    plan = replace(Plan(uuid4(), uuid4(), sample_conditions()), status=status)
    plans.store(plan)
    plans.created_at[plan.id] = FIRST_CREATED_AT - waited
    return plans


def health_of(
    plans: PlanRepository, builds: Sequence[RecordedBuild] = (), now: datetime = FIRST_CREATED_AT
) -> CheckHealth:
    return CheckHealth(plans, FakePlanBuildLog(builds), lambda: now, STALL_AFTER, timedelta(days=7))


def plan_app(
    courses_and_search: tuple[FakeCourseRepository, SearchCourses] | None = None,
    plans: FakePlanRepository | None = None,
    users: FakeUserRepository | None = None,
    health: CheckHealth | None = None,
) -> FastAPI:
    courses, search = courses_and_search or courses_ranked_by({"科目A": 0.9, "科目B": 0.8})
    stored = plans or FakePlanRepository()
    known = users or FakeUserRepository()
    identify = IdentifyUser(FakeTokenVerifier(TOKENS), known)
    return create_app(
        RequestPlan(search, courses, stored, known, 16, QUOTA, lambda: FIRST_CREATED_AT),
        GetPlan(stored),
        ListPlans(stored),
        ListClassChoices(courses, known),
        ListOfferedCourses(courses, known),
        AnswerTakenCourses(stored, known, courses),
        DeletePlan(stored, lambda: FIRST_CREATED_AT),
        SyllabusLinks(courses),
        TakenCourses(known),
        DeleteAccount(known, lambda: FIRST_CREATED_AT),
        identify,
        health or health_of(stored),
        2026,
        API_VERSION,
    )


def plan_api(
    courses_and_search: tuple[FakeCourseRepository, SearchCourses] | None = None,
    plans: FakePlanRepository | None = None,
    users: FakeUserRepository | None = None,
    token: str | None = "token-a",
    health: CheckHealth | None = None,
) -> TestClient:
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return TestClient(
        plan_app(courses_and_search, plans, users, health),
        raise_server_exceptions=False,
        headers=headers,
    )
