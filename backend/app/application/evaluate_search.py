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
        empty = [case.occupation for case in dataset.cases if not case.expected]
        if empty:
            raise EvaluationError(f"期待する科目がありません: {'、'.join(empty)}")
        candidates = self._search.candidates(dataset.year, dataset.department, ALL_GRADES)
        expected = {name for case in dataset.cases for name in case.expected}
        unknown = sorted(expected - candidates.names)
        if unknown:
            raise EvaluationError(f"候補に無い科目名があります: {'、'.join(unknown)}")
        rankings = candidates.rank([case.query for case in dataset.cases], max(RECALL_CUTOFFS))
        results = []
        for case, matches in zip(dataset.cases, rankings, strict=True):
            rank_of = {match.name: rank for rank, match in enumerate(matches, start=1)}
            ranks = tuple((name, rank_of.get(name)) for name in case.expected)
            results.append(CaseResult(case.occupation, ranks))
        return EvaluationReport(tuple(results))
