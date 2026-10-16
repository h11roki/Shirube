from dataclasses import dataclass
from uuid import UUID

from app.domain.recommendation import Recommendation
from app.domain.roadmap import Roadmap, Semester, remaining_semesters


class PlanError(ValueError):
    pass


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
class Plan:
    id: UUID
    owner_id: UUID
    conditions: PlanConditions
    recommendation: Recommendation
    roadmap: Roadmap

    def __post_init__(self) -> None:
        if self.recommendation.profile.occupation != self.conditions.occupation:
            raise PlanError(f"推薦の職業が条件と違います: {self.recommendation.profile.occupation}")
        semesters = tuple(plan.semester for plan in self.roadmap.semesters)
        if semesters != remaining_semesters(self.conditions.start):
            raise PlanError(
                f"道標の学期が {self.conditions.start}から 4 回生 秋学期までになっていません"
            )
        planned = [
            *(placed.course.name for plan in self.roadmap.semesters for placed in plan.courses),
            *(course.name for course in self.roadmap.unplaced),
        ]
        if sorted(planned) != sorted(course.name for course in self.recommendation.courses):
            raise PlanError("推薦の科目が、置いた科目か置けなかった科目に 1 回ずつ入っていません")
        over = [
            str(plan.semester)
            for plan in self.roadmap.semesters
            if plan.credits > self.conditions.credit_limit
        ]
        if over:
            raise PlanError(f"単位の上限を超えた学期があります: {'、'.join(over)}")
