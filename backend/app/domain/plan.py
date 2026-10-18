from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Self
from uuid import UUID

from app.domain.recommendation import Recommendation
from app.domain.roadmap import Roadmap, Semester, remaining_semesters


class PlanError(ValueError):
    pass


class PlanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


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

    def __post_init__(self) -> None:
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
        if semesters != remaining_semesters(self.conditions.start):
            raise PlanError(
                f"道標の学期が {self.conditions.start}から 4 回生 秋学期までになっていません"
            )
        planned = [
            *(placed.course.name for plan in roadmap.semesters for placed in plan.courses),
            *(course.name for course in roadmap.unplaced),
        ]
        if sorted(planned) != sorted(course.name for course in recommendation.courses):
            raise PlanError("推薦の科目が、置いた科目か置けなかった科目に 1 回ずつ入っていません")
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
        return replace(self, status=PlanStatus.SUCCEEDED, result=result)

    def failed(self, failure: str) -> Self:
        if self.status is not PlanStatus.RUNNING:
            raise PlanError(f"作成中でない道標は失敗にできません: {self.status}")
        return replace(self, status=PlanStatus.FAILED, failure=failure)
