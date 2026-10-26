from collections import Counter
from collections.abc import Set
from dataclasses import dataclass, replace

from app.application.ports import OccupationAnalyzer
from app.application.search_courses import SearchCourses
from app.domain.occupation import is_single_line, search_query
from app.domain.roadmap import ALL_SEMESTERS

RECALL_CUTOFFS = (10, 20)


class EvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class EvaluationCase:
    occupation: str
    skills: tuple[str, ...]
    expected: tuple[str, ...]
    interpretation: str | None = None

    def __post_init__(self) -> None:
        if not self.occupation.strip():
            raise EvaluationError("職業名が空です")
        if not is_single_line(self.occupation):
            raise EvaluationError(f"{self.occupation!r}: 職業名に改行があります")
        if self.interpretation is not None and not is_single_line(self.interpretation):
            raise EvaluationError(f"{self.occupation}: 解釈した職業名は空でない 1 行にしてください")
        if not self.skills or not all(skill.strip() for skill in self.skills):
            raise EvaluationError(f"{self.occupation}: スキルが空です")
        if not all(is_single_line(skill) for skill in self.skills):
            raise EvaluationError(f"{self.occupation}: スキルに改行があります")
        if len({skill.strip() for skill in self.skills}) != len(self.skills):
            raise EvaluationError(f"{self.occupation}: スキルが重複しています")
        if not self.expected:
            raise EvaluationError(f"{self.occupation}: 期待する科目がありません")

    @property
    def query(self) -> str:
        named = self.occupation if self.interpretation is None else self.interpretation
        return search_query(named, self.skills)


@dataclass(frozen=True)
class EvaluationDataset:
    year: int
    department: str
    cases: tuple[EvaluationCase, ...]

    def __post_init__(self) -> None:
        if not self.cases:
            raise EvaluationError("評価する職業がありません")
        counts = Counter(case.occupation for case in self.cases)
        duplicated = sorted(name for name, count in counts.items() if count > 1)
        if duplicated:
            raise EvaluationError(f"同じ職業が 2 回あります: {'、'.join(duplicated)}")

    def require_courses_in(self, names: Set[str]) -> None:
        unknown = sorted({name for case in self.cases for name in case.expected} - names)
        if unknown:
            raise EvaluationError(f"候補に無い科目名があります: {'、'.join(unknown)}")


def with_analyzed_profiles(
    dataset: EvaluationDataset, analyzer: OccupationAnalyzer
) -> EvaluationDataset:
    profiles = [analyzer.analyze(case.occupation) for case in dataset.cases]
    cases = tuple(
        replace(case, interpretation=profile.interpretation, skills=profile.skills)
        for case, profile in zip(dataset.cases, profiles, strict=True)
    )
    return replace(dataset, cases=cases)


@dataclass(frozen=True)
class CaseResult:
    occupation: str
    query: str
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
        candidates = self._search.candidates(dataset.year, dataset.department, ALL_SEMESTERS)
        dataset.require_courses_in(candidates.names)
        rankings = candidates.pick(dataset.cases, max(RECALL_CUTOFFS))
        results = []
        for case, matches in zip(dataset.cases, rankings, strict=True):
            rank_of = {match.name: rank for rank, match in enumerate(matches, start=1)}
            ranks = tuple((name, rank_of.get(name)) for name in case.expected)
            results.append(CaseResult(case.occupation, case.query, ranks))
        return EvaluationReport(tuple(results))
