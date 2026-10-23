import argparse
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.application.judging import (
    JUDGES,
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
    course_document,
    judged_courses,
    read_document,
    write_document,
)
from app.presentation.cli.labels import RELEVANCE_LABELS
from app.presentation.composition import database_engine, load_settings

LABELS = {label: relevance for relevance, label in RELEVANCE_LABELS.items()}
PART_FILES = ("courses-1.json", "courses-2.json")
OCCUPATION_FILE = "occupation-names.json"
UNREADABLE = (OSError, ValueError, KeyError, TypeError, AttributeError)


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
            if label not in LABELS:
                raise JudgingError(
                    f"{role} / {occupation}: 中心と土台のほかの分け方があります: {label}"
                )
            for entry in entries:
                if entry["course"] in courses:
                    raise JudgingError(
                        f"{role} / {occupation}: 同じ科目に票が 2 つあります: {entry['course']}"
                    )
                courses[entry["course"]] = Vote(LABELS[label], entry["evidence"])
        votes[occupation] = courses
    return JudgeOutput(keys[role], votes)


def undecided_courses(judged: Mapping[str, Sequence[JudgedCourse]]) -> list[str]:
    return [
        f"{occupation} / {course.name}"
        for occupation, courses in judged.items()
        for course in courses
        if course.undecided
    ]


def material_pages(directory: Path, judgments: Mapping[str, Any]) -> dict[str, str]:
    parts = [read_document(directory / name) for name in PART_FILES]
    if [[material["name"] for material in part] for part in parts] != judgments["parts"]:
        raise JudgingError("資料の科目が判定の前半と後半と違います(materials で作り直す)")
    pages = {material["name"]: material["page"] for part in parts for material in part}
    stale = sorted(
        {
            course["name"]
            for occupation in judgments["occupations"]
            for course in occupation["courses"]
            if pages.get(course["name"]) != course["page"]
        }
    )
    if stale:
        raise JudgingError(
            f"資料のシラバスが判定と違う科目があります: {'、'.join(stale)}(materials で作り直す)"
        )
    return pages


def _read(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        dataset, judgments = read_document(args.dataset), read_document(args.judgments)
        occupation_counts = {
            "評価データ": Counter(occupation["name"] for occupation in dataset["occupations"]),
            "判定": Counter(occupation["name"] for occupation in judgments["occupations"]),
        }
        same_place = (dataset["year"], dataset["department"]) == (
            judgments["year"],
            judgments["department"],
        )
    except UNREADABLE as error:
        sys.exit(f"評価データか判定を読めません: {error!r}")
    if not same_place:
        sys.exit("評価データと判定の年度か学科が違います")
    for where, counts in occupation_counts.items():
        repeated = sorted(name for name, count in counts.items() if count > 1)
        if repeated:
            sys.exit(f"{where}に同じ職業が 2 回あります: {'、'.join(repeated)}")
    return dataset, judgments


def _documents(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    dataset, judgments = _read(args)
    names = unjudged(dataset, judgments)
    if not names:
        sys.exit("判定していない職業がありません(評価データに職業を足してから流す)")
    return dataset, judgments, names


def _rebuild(dataset: Mapping[str, Any], judged: Mapping[str, Sequence[JudgedCourse]]) -> None:
    for occupation in dataset["occupations"]:
        occupation["expected"] = expected_courses(judged[occupation["name"]])


def _save(path: Path, document: Mapping[str, Any], one_line: frozenset[str]) -> None:
    try:
        write_document(path, document, one_line)
    except OSError as error:
        sys.exit(
            f"書けません: {error}"
            "(判定を書いたあとなら、期待する科目は judging expected で作り直せる)"
        )


def _materials(args: argparse.Namespace) -> None:
    dataset, judgments, names = _documents(args)
    engine = database_engine(load_settings())
    try:
        materials = JudgingMaterials(SqlCourseRepository(engine)).courses(
            dataset["year"], dataset["department"]
        )
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
    except JudgingError as error:
        sys.exit(str(error))
    except OperationalError as error:
        sys.exit(f"DB に接続できません: {error.orig}")
    except SQLAlchemyError as error:
        sys.exit(f"DB の操作に失敗しました: {error}")
    except UNREADABLE as error:
        sys.exit(f"資料を作れません: {error!r}")
    finally:
        engine.dispose()
    print(
        f"科目 {len(materials)}(前半 {len(halves[0])}、後半 {len(halves[1])})と、"
        f"判定する職業 {len(names)} を {args.out} に書いた"
    )


def _merge(args: argparse.Namespace) -> None:
    dataset, judgments, names = _documents(args)
    try:
        judges = judgments["judges"]
        if sorted(judges) != sorted(JUDGES):
            raise JudgingError(
                f"判定者の一覧が {'、'.join(JUDGES)} と違います: {'、'.join(judges)}"
            )
        pages = material_pages(args.materials, judgments)
        given = [
            [judge_output(read_document(path), judges) for path in paths]
            for paths in (args.first, args.second)
        ]
        chosen = read_document(args.decisions) if args.decisions else {}
        mentioned = {
            occupation for half in given for output in half for occupation in output.votes
        } | chosen.keys()
        again = sorted(mentioned & {occupation["name"] for occupation in judgments["occupations"]})
        if again:
            raise JudgingError(
                f"判定済みの職業の票か決定があります: {'、'.join(again)}"
                "(判定済みの職業は judgments.json を直して judging expected を流す)"
            )
        dropped = sorted(mentioned - set(names))
        halves = [
            [
                JudgeOutput(
                    output.judge,
                    {name: votes for name, votes in output.votes.items() if name in names},
                )
                for output in half
            ]
            for half in given
        ]
        decisions = {
            occupation: {course: Relevance(label) for course, label in courses.items()}
            for occupation, courses in chosen.items()
            if occupation in names
        }
        judged = decide(combine(halves, judgments["parts"], pages, names), decisions)
        earlier = {
            occupation["name"]: judged_courses(occupation)
            for occupation in judgments["occupations"]
        }
    except JudgingError as error:
        sys.exit(f"判定の決まりに合いません: {error}")
    except UNREADABLE as error:
        sys.exit(f"判定者の出力か決定を読めません: {error!r}")
    if dropped:
        print(f"評価データに無い職業の票と決定は使わない: {'、'.join(dropped)}")
    if missing := undecided_courses(earlier):
        sys.exit(
            f"判定に決定の足りない科目があります: {'、'.join(missing)}"
            "(judgments.json の decision を確かめる)"
        )
    if undecided_courses(judged):
        print("中心が 1 票だけの科目を、中心(core)か土台(foundation)に決めてください")
        for occupation, courses in judged.items():
            for course in courses:
                if course.undecided:
                    votes = "、".join(
                        f"{judges[judge]} {RELEVANCE_LABELS[vote.label]}「{vote.evidence}」"
                        for judge, vote in course.votes.items()
                    )
                    print(f"  {occupation} / {course.name}: {votes}")
        sys.exit(1)
    expected = {name: expected_courses(judged[name]) for name in names}
    empty = [name for name, courses in expected.items() if not courses]
    if empty:
        sys.exit(
            f"期待する科目が 1 つも無い職業があります: {'、'.join(empty)}"
            "(再現率を測れないので、評価データから外すか入れ替える)"
        )
    judgments["occupations"] += [
        {"name": name, "courses": [course_document(course) for course in judged[name]]}
        for name in names
    ]
    _rebuild(dataset, {**earlier, **judged})
    _save(args.judgments, judgments, frozenset(JUDGES))
    _save(args.dataset, dataset, DATASET_LINES)
    print(
        f"判定に {len(names)} 職業を足し、期待する科目を作り直した: "
        + "、".join(f"{name} {len(expected[name])}" for name in names)
    )


def _expected(args: argparse.Namespace) -> None:
    dataset, judgments = _read(args)
    try:
        judged = {
            occupation["name"]: judged_courses(occupation)
            for occupation in judgments["occupations"]
        }
    except JudgingError as error:
        sys.exit(f"判定の決まりに合いません: {error}")
    except UNREADABLE as error:
        sys.exit(f"判定を読めません: {error!r}")
    if missing := unjudged(dataset, judgments):
        sys.exit(f"判定に無い職業があります: {'、'.join(missing)}(materials と merge で判定する)")
    if undecided := undecided_courses(judged):
        sys.exit(
            f"判定に決定の足りない科目があります: {'、'.join(undecided)}"
            "(judgments.json の decision を確かめる)"
        )
    _rebuild(dataset, judged)
    _save(args.dataset, dataset, DATASET_LINES)
    print(f"{len(judged)} 職業の期待する科目を判定から作り直した")


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
    expected = commands.add_parser("expected", help="全ての職業の期待する科目を判定から作り直す")
    expected.set_defaults(handle=_expected)
    args = parser.parse_args(argv)
    args.handle(args)


if __name__ == "__main__":
    main()
