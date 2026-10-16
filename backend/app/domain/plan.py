from dataclasses import dataclass
from uuid import UUID

from app.domain.recommendation import Recommendation
from app.domain.roadmap import Roadmap, Semester


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
    conditions: PlanConditions
    recommendation: Recommendation
    roadmap: Roadmap

    def __post_init__(self) -> None:
        if self.recommendation.profile.occupation != self.conditions.occupation:
            raise PlanError(f"推薦の職業が条件と違います: {self.recommendation.profile.occupation}")
        semesters = [plan.semester for plan in self.roadmap.semesters]
        if semesters[:1] != [self.conditions.start]:
            raise PlanError(f"道標が始める学期から始まっていません: {self.conditions.start}")
