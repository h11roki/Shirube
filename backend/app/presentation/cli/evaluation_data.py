import json
from collections import Counter
from collections.abc import Mapping, Set
from pathlib import Path
from typing import Any

from app.application.evaluate_search import EvaluationCase, EvaluationDataset
from app.application.evaluate_selection import Judgment, Judgments, judgment_of
from app.application.judging import JudgedCourse, Vote
from app.domain.recommendation import Relevance

DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "eval" / "occupations.json"
DEFAULT_JUDGMENTS = DEFAULT_DATASET.with_name("judgments.json")
DATASET_LINES = frozenset({"skills"})


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    counts = Counter(key for key, _ in pairs)
    duplicated = sorted(key for key, count in counts.items() if count > 1)
    if duplicated:
        raise ValueError(f"同じ項目が 2 回あります: {'、'.join(duplicated)}")
    return dict(pairs)


def read_document(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def write_document(path: Path, document: Any, one_line: Set[str]) -> None:
    written = path.with_name(f".{path.name}.writing")
    written.write_text(_dumped(document, 0, one_line) + "\n", encoding="utf-8")
    written.replace(path)


def _dumped(value: Any, indent: int, one_line: Set[str]) -> str:
    inner = " " * (indent + 2)
    if isinstance(value, dict) and value:
        items = [
            f"{inner}{json.dumps(key, ensure_ascii=False)}: "
            + (
                json.dumps(item, ensure_ascii=False)
                if key in one_line
                else _dumped(item, indent + 2, one_line)
            )
            for key, item in value.items()
        ]
        return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"
    if isinstance(value, list) and value:
        items = [inner + _dumped(item, indent + 2, one_line) for item in value]
        return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"
    return json.dumps(value, ensure_ascii=False)


def load_dataset(path: Path) -> EvaluationDataset:
    document = read_document(path)
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


def judged_courses(occupation: Mapping[str, Any]) -> list[JudgedCourse]:
    return [
        JudgedCourse(
            course["name"],
            course["page"],
            {
                judge: Vote(Relevance(vote["label"]), vote["evidence"])
                for judge, vote in course["votes"].items()
            },
            None if course.get("decision") is None else Relevance(course["decision"]),
        )
        for course in occupation["courses"]
    ]


def course_document(course: JudgedCourse) -> dict[str, Any]:
    document: dict[str, Any] = {
        "name": course.name,
        "page": course.page,
        "votes": {
            judge: {"label": vote.label.value, "evidence": vote.evidence}
            for judge, vote in course.votes.items()
        },
    }
    if course.decision is not None:
        document["decision"] = course.decision.value
    return document


def load_judgments(path: Path, dataset: EvaluationDataset) -> Judgments:
    document = read_document(path)
    if (document["year"], document["department"]) != (dataset.year, dataset.department):
        raise ValueError("判定の年度と学科が評価データと違います")
    by_course: dict[tuple[str, str], Judgment] = {}
    for occupation in document["occupations"]:
        for course in judged_courses(occupation):
            key = (occupation["name"], course.name)
            if key in by_course:
                raise ValueError(f"同じ科目の判定が 2 回あります: {key}")
            if course.undecided:
                raise ValueError(f"中心が 1 票だけの科目に決定がありません: {key}")
            by_course[key] = judgment_of(
                [vote.label for vote in course.votes.values()], course.decision
            )
    courses = frozenset(name for part in document["parts"] for name in part)
    return Judgments(courses, by_course)
