from collections.abc import Sequence, Set
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from app.domain.course import CourseSection
from app.domain.recommendation import Recommendation
from app.domain.roadmap import Roadmap, Semester, place, remaining_semesters


class PlanError(ValueError):
    pass


class PlanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PlanStage(StrEnum):
    ANALYZING = "analyzing"
    SEARCHING = "searching"
    SELECTING = "selecting"
    PLACING = "placing"


@dataclass(frozen=True)
class PlanConditions:
    occupation: str
    department: str
    year: int
    start: Semester
    chosen_classes: tuple[tuple[str, str], ...]
    credit_limit: int

    def __post_init__(self) -> None:
        names = [name for name, _ in self.chosen_classes]
        if names != sorted(set(names)):
            raise PlanError("クラスの選択は科目名の順に、科目ごとに 1 つにしてください")

    @property
    def semesters(self) -> tuple[Semester, ...]:
        return remaining_semesters(self.start)

    def roadmap(
        self,
        recommendation: Recommendation,
        sections: Sequence[CourseSection],
        taken: Set[str] = frozenset(),
    ) -> Roadmap:
        return place(
            recommendation,
            sections,
            self.department,
            self.year,
            self.semesters,
            self.credit_limit,
            dict(self.chosen_classes),
            taken,
        )


@dataclass(frozen=True)
class PlanResult:
    recommendation: Recommendation
    roadmap: Roadmap


@dataclass(frozen=True)
class Plan:
    id: UUID
    owner_id: UUID
    conditions: PlanConditions
    status: PlanStatus = PlanStatus.PENDING
    result: PlanResult | None = None
    failure: str | None = None
    stage: PlanStage | None = None

    def __post_init__(self) -> None:
        if self.stage is not None and self.status is not PlanStatus.RUNNING:
            raise PlanError(f"段を持つのは作成中の道標だけです: {self.status}")
        if (self.result is not None) != (self.status is PlanStatus.SUCCEEDED):
            raise PlanError(f"結果を持つのは完了した道標だけです: {self.status}")
        if (self.failure is not None) != (self.status is PlanStatus.FAILED):
            raise PlanError(f"失敗の文を持つのは失敗した道標だけです: {self.status}")
        if self.result is None:
            return
        recommendation, roadmap = self.result.recommendation, self.result.roadmap
        if recommendation.profile.occupation != self.conditions.occupation:
            raise PlanError(f"推薦の職業が条件と違います: {recommendation.profile.occupation}")
        semesters = tuple(plan.semester for plan in roadmap.semesters)
        if semesters != self.conditions.semesters:
            raise PlanError(
                f"道標の学期が {self.conditions.start}から 4 回生 秋学期までになっていません"
            )
        planned = [
            *(placed.course.name for plan in roadmap.semesters for placed in plan.courses),
            *(course.name for course in roadmap.unplaced),
            *(course.name for course in roadmap.taken),
        ]
        if sorted(planned) != sorted(course.name for course in recommendation.courses):
            raise PlanError(
                "推薦の科目が、置いた科目、置けなかった科目、もう取った科目のどれかに"
                " 1 回ずつ入っていません"
            )
        over = [
            str(plan.semester)
            for plan in roadmap.semesters
            if plan.credits > self.conditions.credit_limit
        ]
        if over:
            raise PlanError(f"単位の上限を超えた学期があります: {'、'.join(over)}")

    def succeeded(self, result: PlanResult) -> Self:
        if self.status is not PlanStatus.RUNNING:
            raise PlanError(f"作成中でない道標は完了にできません: {self.status}")
        return replace(self, status=PlanStatus.SUCCEEDED, result=result, stage=None)

    def placed_again(self, roadmap: Roadmap) -> Self:
        if self.result is None:
            raise PlanError(f"完了していない道標は置き直せません: {self.status}")
        return replace(self, result=replace(self.result, roadmap=roadmap))

    def failed(self, failure: str) -> Self:
        if self.status is not PlanStatus.RUNNING:
            raise PlanError(f"作成中でない道標は失敗にできません: {self.status}")
        return replace(self, status=PlanStatus.FAILED, failure=failure, stage=None)


@dataclass(frozen=True)
class PlanSummary:
    id: UUID
    status: PlanStatus
    occupation: str
    start: Semester
    created_at: datetime
