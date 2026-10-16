import json
from collections import Counter
from pathlib import Path

from app.application.evaluate_search import EvaluationCase, EvaluationDataset
from app.application.evaluate_selection import Judgment, Judgments, judgment_of
from app.domain.recommendation import Relevance

DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "eval" / "occupations.json"
DEFAULT_JUDGMENTS = DEFAULT_DATASET.with_name("judgments.json")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    counts = Counter(key for key, _ in pairs)
    duplicated = sorted(key for key, count in counts.items() if count > 1)
    if duplicated:
        raise ValueError(f"同じ項目が 2 回あります: {'、'.join(duplicated)}")
    return dict(pairs)


def load_dataset(path: Path) -> EvaluationDataset:
    document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    year, department = document["year"], document["department"]
    if isinstance(year, bool) or not isinstance(year, int) or not isinstance(department, str):
        raise ValueError("year は整数、department は文字列にしてください")
    cases = []
    for occupation in document["occupations"]:
        name, skills, expected = occupation["name"], occupation["skills"], occupation["expected"]
        if not isinstance(name, str):
            raise ValueError(f"name は文字列にしてください: {name!r}")
        if not isinstance(skills, list) or not all(isinstance(skill, str) for skill in skills):
            raise ValueError(f"{name}: skills は文字列の配列にしてください")
        if not isinstance(expected, dict) or not all(
            isinstance(why, str) and why.strip() for why in expected.values()
        ):
            raise ValueError(
                f"{name}: expected は科目名から理由(空でない文字列)への対応にしてください"
            )
        cases.append(EvaluationCase(name, tuple(skills), tuple(expected)))
    return EvaluationDataset(year, department, tuple(cases))


def load_judgments(path: Path, dataset: EvaluationDataset) -> Judgments:
    document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    if (document["year"], document["department"]) != (dataset.year, dataset.department):
        raise ValueError("判定の年度と学科が評価データと違います")
    by_course: dict[tuple[str, str], Judgment] = {}
    for occupation in document["occupations"]:
        for course in occupation["courses"]:
            key = (occupation["name"], course["name"])
            if key in by_course:
                raise ValueError(f"同じ科目の判定が 2 回あります: {key}")
            votes = [Relevance(vote["label"]) for vote in course["votes"].values()]
            decision = course.get("decision")
            decided = None if decision is None else Relevance(decision)
            if (decided is not None) != (votes.count(Relevance.CORE) == 1):
                raise ValueError(f"決定は中心の票が 1 つだけの科目にだけ付けます: {key}")
            by_course[key] = judgment_of(votes, decided)
    courses = frozenset(name for part in document["parts"] for name in part)
    return Judgments(courses, by_course)
