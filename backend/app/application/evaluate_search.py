from collections import Counter
from collections.abc import Set
from dataclasses import dataclass

from app.application.ports import OccupationAnalyzer
from app.application.search_courses import SearchCourses
from app.domain.occupation import SKILL_COUNT, OccupationProfile, is_single_line
from app.domain.ranking import CourseMatch
from app.domain.roadmap import ALL_SEMESTERS

RECALL_CUTOFFS = (10, 20)


class EvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class EvaluationCase:
    occupation: str
    skills: tuple[str, ...]
    expected: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.occupation.strip():
            raise EvaluationError("職業名が空です")
        if not is_single_line(self.occupation):
            raise EvaluationError(f"{self.occupation!r}: 職業名に改行があります")
        if not self.skills or not all(skill.strip() for skill in self.skills):
            raise EvaluationError(f"{self.occupation}: スキルが空です")
        if not all(is_single_line(skill) for skill in self.skills):
            raise EvaluationError(f"{self.occupation}: スキルに改行があります")
        if len({skill.strip() for skill in self.skills}) != len(self.skills):
            raise EvaluationError(f"{self.occupation}: スキルが重複しています")
        if len(self.skills) not in SKILL_COUNT:
            counts = f"{SKILL_COUNT.start}〜{SKILL_COUNT.stop - 1}"
            raise EvaluationError(f"{self.occupation}: スキルは {counts} 個にしてください")
        if not self.expected:
            raise EvaluationError(f"{self.occupation}: 期待する科目がありません")


@dataclass(frozen=True)
class EvaluationDataset:
    year: int
    department: str
    cases: tuple[EvaluationCase, ...]
    heldout: bool = False

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


class HandwrittenProfiles:
    def __init__(self, dataset: EvaluationDataset) -> None:
        self._profiles = {
            case.occupation: OccupationProfile(case.occupation, case.occupation, None, case.skills)
            for case in dataset.cases
        }

    def analyze(self, occupation: str) -> OccupationProfile:
        return self._profiles[occupation]


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
    def __init__(self, search: SearchCourses, profiles: OccupationAnalyzer) -> None:
        self._search = search
        self._profiles = profiles

    def rankings(
        self, dataset: EvaluationDataset, limit: int
    ) -> list[tuple[OccupationProfile, list[CourseMatch]]]:
        candidates = self._search.candidates(dataset.year, dataset.department, ALL_SEMESTERS)
        dataset.require_courses_in(candidates.names)
        profiles = [self._profiles.analyze(case.occupation) for case in dataset.cases]
        return list(zip(profiles, candidates.pick(profiles, limit), strict=True))

    def run(self, dataset: EvaluationDataset) -> EvaluationReport:
        rankings = self.rankings(dataset, max(RECALL_CUTOFFS))
        results = []
        for case, (profile, matches) in zip(dataset.cases, rankings, strict=True):
            rank_of = {match.name: rank for rank, match in enumerate(matches, start=1)}
            ranks = tuple((name, rank_of.get(name)) for name in case.expected)
            results.append(CaseResult(case.occupation, profile.query, ranks))
        return EvaluationReport(tuple(results))
