import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.judging import (
    JudgedCourse,
    JudgeOutput,
    JudgingError,
    JudgingMaterials,
    Vote,
    combine,
    decide,
    expected_courses,
)
from app.domain.recommendation import Relevance
from app.infrastructure.db.courses import SqlCourseRepository
from app.presentation.cli.evaluation_data import (
    DATASET_LINES,
    DEFAULT_DATASET,
    DEFAULT_JUDGMENTS,
    read_document,
    write_document,
)
from app.presentation.cli.labels import RELEVANCE_LABELS
from app.presentation.composition import database_engine, load_settings

LABELS = {label: relevance for relevance, label in RELEVANCE_LABELS.items()}
PART_FILES = ("courses-1.json", "courses-2.json")
OCCUPATION_FILE = "occupations.json"


def unjudged(dataset: Mapping[str, Any], judgments: Mapping[str, Any]) -> list[str]:
    judged = {occupation["name"] for occupation in judgments["occupations"]}
    return [
        occupation["name"]
        for occupation in dataset["occupations"]
        if occupation["name"] not in judged
    ]


def judge_output(document: Mapping[str, Any], judges: Mapping[str, str]) -> JudgeOutput:
    keys = {role: key for key, role in judges.items()}
    role = document["judge"]
    if role not in keys:
        raise JudgingError(f"判定者の立場が判定の一覧にありません: {role}")
    votes: dict[str, dict[str, Vote]] = {}
    for occupation, labelled in document["judgments"].items():
        courses: dict[str, Vote] = {}
        for label, entries in labelled.items():
            for entry in entries:
                if entry["course"] in courses:
                    raise JudgingError(
                        f"{role} / {occupation}: 同じ科目に票が 2 つあります: {entry['course']}"
                    )
                courses[entry["course"]] = Vote(LABELS[label], entry["evidence"])
        votes[occupation] = courses
    return JudgeOutput(keys[role], votes)


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


def undecided_text(judged: Mapping[str, Sequence[JudgedCourse]], judges: Mapping[str, str]) -> str:
    lines = ["中心が 1 票だけの科目を、中心(core)か土台(foundation)に決めてください"]
    for occupation, courses in judged.items():
        for course in courses:
            if course.undecided:
                votes = "、".join(
                    f"{judges[judge]} {RELEVANCE_LABELS[vote.label]}「{vote.evidence}」"
                    for judge, vote in course.votes.items()
                )
                lines.append(f"  {occupation} / {course.name}: {votes}")
    return "\n".join(lines)


def _documents(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    try:
        dataset, judgments = read_document(args.dataset), read_document(args.judgments)
        names = unjudged(dataset, judgments)
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"評価データか判定を読めません: {error!r}")
    if not names:
        sys.exit("判定していない職業がありません(評価データに職業を足してから流す)")
    return dataset, judgments, names


def _materials(args: argparse.Namespace) -> None:
    dataset, judgments, names = _documents(args)
    engine = database_engine(load_settings())
    try:
        materials = JudgingMaterials(SqlCourseRepository(engine)).courses(
            dataset["year"], dataset["department"]
        )
    except JudgingError as error:
        sys.exit(str(error))
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    finally:
        engine.dispose()
    half = (len(materials) + 1) // 2
    halves = [materials[:half], materials[half:]]
    if [[material.name for material in part] for part in halves] != judgments["parts"]:
        sys.exit(
            "候補の科目が判定の前半と後半と違います"
            "(時間割表かシラバスを取り込み直したなら、判定もやり直す)"
        )
    args.out.mkdir(parents=True, exist_ok=True)
    for name, part in zip(PART_FILES, halves, strict=True):
        (args.out / name).write_text(
            json.dumps([asdict(material) for material in part], ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
    (args.out / OCCUPATION_FILE).write_text(
        json.dumps(names, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"科目 {len(materials)}(前半 {len(halves[0])}、後半 {len(halves[1])})と、"
        f"判定する職業 {len(names)} を {args.out} に書いた"
    )


def _merge(args: argparse.Namespace) -> None:
    dataset, judgments, names = _documents(args)
    judges = judgments["judges"]
    try:
        pages = {
            material["name"]: material["page"]
            for name in PART_FILES
            for material in read_document(args.materials / name)
        }
        halves = [
            [judge_output(read_document(path), judges) for path in paths]
            for paths in (args.first, args.second)
        ]
        chosen = read_document(args.decisions) if args.decisions else {}
        decisions = {
            occupation: {course: Relevance(label) for course, label in courses.items()}
            for occupation, courses in chosen.items()
        }
        judged = decide(combine(halves, list(judges), judgments["parts"], pages, names), decisions)
    except (OSError, ValueError, KeyError, TypeError) as error:
        sys.exit(f"判定者の出力か決定を読めません: {error}")
    if any(course.undecided for courses in judged.values() for course in courses):
        print(undecided_text(judged, judges))
        sys.exit(1)
    empty = [name for name in names if not expected_courses(judged[name])]
    if empty:
        sys.exit(
            f"期待する科目が 1 つも無い職業があります: {'、'.join(empty)}"
            "(再現率を測れないので、評価データから外すか入れ替える)"
        )
    judgments["occupations"] += [
        {"name": name, "courses": [course_document(course) for course in judged[name]]}
        for name in names
    ]
    every = {
        occupation["name"]: judged_courses(occupation) for occupation in judgments["occupations"]
    }
    for occupation in dataset["occupations"]:
        occupation["expected"] = expected_courses(every[occupation["name"]])
    write_document(args.judgments, judgments, frozenset(judges))
    write_document(args.dataset, dataset, DATASET_LINES)
    print(
        f"判定に {len(names)} 職業を足し、期待する科目を作り直した: "
        + "、".join(f"{name} {len(expected_courses(judged[name]))}" for name in names)
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="評価データの判定の資料を作り、判定をまとめる")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--judgments", type=Path, default=DEFAULT_JUDGMENTS)
    commands = parser.add_subparsers(dest="command", required=True)
    materials = commands.add_parser(
        "materials", help="判定していない職業について、判定者に渡す科目と職業の資料を書く"
    )
    materials.add_argument("--out", type=Path, required=True)
    materials.set_defaults(handle=_materials)
    merge = commands.add_parser(
        "merge", help="判定者の出力と決定を判定にまとめ、期待する科目を作り直す"
    )
    merge.add_argument("--first", type=Path, nargs="+", required=True)
    merge.add_argument("--second", type=Path, nargs="+", required=True)
    merge.add_argument("--materials", type=Path, required=True)
    merge.add_argument("--decisions", type=Path)
    merge.set_defaults(handle=_merge)
    args = parser.parse_args(argv)
    args.handle(args)


if __name__ == "__main__":
    main()
