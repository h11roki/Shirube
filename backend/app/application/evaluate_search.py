from dataclasses import dataclass

from app.application.search_courses import SearchCourses
from app.domain.course import ALL_GRADES

RECALL_CUTOFFS = (10, 20)


class EvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class EvaluationCase:
    occupation: str
    skills: tuple[str, ...]
    expected: tuple[str, ...]

    @property
    def query(self) -> str:
        return "\n".join((self.occupation, *self.skills))


@dataclass(frozen=True)
class EvaluationDataset:
    year: int
    department: str
    cases: tuple[EvaluationCase, ...]


@dataclass(frozen=True)
class CaseResult:
    occupation: str
    ranks: tuple[tuple[str, int | None], ...]

    def recall(self, cutoff: int) -> float:
        found = sum(1 for _, rank in self.ranks if rank is not None and rank <= cutoff)
        return found / len(self.ranks)


@dataclass(frozen=True)
class EvaluationReport:
    results: tuple[CaseResult, ...]

    def mean_recall(self, cutoff: int) -> float:
        return sum(result.recall(cutoff) for result in self.results) / len(self.results)


class EvaluateSearch:
    def __init__(self, search: SearchCourses) -> None:
        self._search = search

    def run(self, dataset: EvaluationDataset) -> EvaluationReport:
        if not dataset.cases:
            raise EvaluationError("評価する職業がありません")
        year, department = dataset.year, dataset.department
        candidates = self._search.candidates(year, department, ALL_GRADES)
        unknown = sorted({name for case in dataset.cases for name in case.expected} - candidates)
        if unknown:
            raise EvaluationError(f"候補に無い科目名があります: {'、'.join(unknown)}")
        results = []
        for case in dataset.cases:
            matches = self._search.run(
                year, case.query, department, ALL_GRADES, max(RECALL_CUTOFFS)
            )
            rank_of = {match.name: rank for rank, match in enumerate(matches, start=1)}
            results.append(
                CaseResult(
                    case.occupation, tuple((name, rank_of.get(name)) for name in case.expected)
                )
            )
        return EvaluationReport(tuple(results))
