import json
from pathlib import Path
from typing import Any

import pytest

from app.presentation.cli.evaluation_data import (
    DATASET_LINES,
    DEFAULT_DATASET,
    DEFAULT_JUDGMENTS,
    read_document,
    write_document,
)
from app.presentation.cli.judging import main

ROLES = {
    "engineer": "採用・育成担当のエンジニア",
    "professor": "カリキュラムを設計する教員",
    "student": "進路を考える 3 回生",
}


@pytest.mark.parametrize(
    ("path", "one_line"),
    [(DEFAULT_DATASET, DATASET_LINES), (DEFAULT_JUDGMENTS, frozenset(ROLES))],
    ids=["dataset", "judgments"],
)
def test_the_committed_files_are_written_back_unchanged(
    tmp_path: Path, path: Path, one_line: frozenset[str]
) -> None:
    written = tmp_path / path.name

    write_document(written, read_document(path), one_line)

    assert written.read_text(encoding="utf-8") == path.read_text(encoding="utf-8")


def test_the_committed_judges_are_the_three_documented_roles() -> None:
    assert read_document(DEFAULT_JUDGMENTS)["judges"] == ROLES


def vote(label: str, evidence: str) -> dict[str, str]:
    return {"label": label, "evidence": evidence}


def judging_files(directory: Path) -> tuple[Path, Path, Path]:
    dataset = directory / "occupations.json"
    judgments = directory / "judgments.json"
    materials = directory / "materials"
    materials.mkdir()
    write_document(
        dataset,
        {
            "year": 2026,
            "department": "情",
            "occupations": [
                {"name": "職業甲", "skills": ["甲"], "expected": {"科目A": "教員の根拠"}},
                {"name": "職業乙", "skills": ["乙"], "expected": {}},
            ],
        },
        DATASET_LINES,
    )
    write_document(
        judgments,
        {
            "year": 2026,
            "department": "情",
            "judges": ROLES,
            "parts": [["科目A", "科目B"], ["科目C", "科目D"]],
            "occupations": [
                {
                    "name": "職業甲",
                    "courses": [
                        {
                            "name": "科目A",
                            "page": "1",
                            "votes": {judge: vote("core", "教員の根拠") for judge in ROLES},
                        }
                    ],
                }
            ],
        },
        frozenset(ROLES),
    )
    for name, courses in (
        ("courses-1.json", ("科目A", "科目B")),
        ("courses-2.json", ("科目C", "科目D")),
    ):
        (materials / name).write_text(
            json.dumps([{"name": course, "page": course[-1]} for course in courses]),
            encoding="utf-8",
        )
    return dataset, judgments, materials


def judge_outputs(directory: Path, first: dict[str, Any], second: dict[str, Any]) -> list[str]:
    arguments: list[str] = []
    for flag, index, half in (("--first", 1, first), ("--second", 2, second)):
        arguments.append(flag)
        for key, role in ROLES.items():
            path = directory / f"{key}-{index}.json"
            path.write_text(
                json.dumps({"judge": role, "judgments": half[key]}, ensure_ascii=False),
                encoding="utf-8",
            )
            arguments.append(str(path))
    return arguments


CORE_B = {
    key: {"職業乙": {"中心": [{"course": "科目B", "evidence": f"{key}のB"}], "土台": []}}
    for key in ROLES
}
SPLIT = {
    "engineer": {"職業乙": {"中心": [{"course": "科目C", "evidence": "エンジニアのC"}]}},
    "professor": {"職業乙": {"土台": [{"course": "科目C", "evidence": "教員のC"}]}},
    "student": {"職業乙": {}},
}


def merge(dataset: Path, judgments: Path, materials: Path, *rest: str) -> None:
    main(
        [
            "--dataset",
            str(dataset),
            "--judgments",
            str(judgments),
            "merge",
            *rest,
            "--materials",
            str(materials),
        ]
    )


def test_merge_asks_for_decisions_before_writing_anything(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset, judgments, materials = judging_files(tmp_path)
    before = judgments.read_text(encoding="utf-8")

    with pytest.raises(SystemExit) as stopped:
        merge(dataset, judgments, materials, *judge_outputs(tmp_path, CORE_B, SPLIT))

    assert stopped.value.code == 1
    assert capsys.readouterr().out.splitlines()[1:] == [
        "  職業乙 / 科目C: 採用・育成担当のエンジニア 中心「エンジニアのC」、"
        "カリキュラムを設計する教員 土台「教員のC」"
    ]
    assert judgments.read_text(encoding="utf-8") == before


def test_merge_adds_the_new_occupation_and_rebuilds_every_expected_course(tmp_path: Path) -> None:
    dataset, judgments, materials = judging_files(tmp_path)
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps({"職業乙": {"科目C": "core"}}), encoding="utf-8")

    merge(
        dataset,
        judgments,
        materials,
        *judge_outputs(tmp_path, CORE_B, SPLIT),
        "--decisions",
        str(decisions),
    )

    added = read_document(judgments)["occupations"][1]
    assert added == {
        "name": "職業乙",
        "courses": [
            {
                "name": "科目B",
                "page": "B",
                "votes": {key: vote("core", f"{key}のB") for key in ROLES},
            },
            {
                "name": "科目C",
                "page": "C",
                "votes": {
                    "engineer": vote("core", "エンジニアのC"),
                    "professor": vote("foundation", "教員のC"),
                },
                "decision": "core",
            },
        ],
    }
    assert [occupation["expected"] for occupation in read_document(dataset)["occupations"]] == [
        {"科目A": "教員の根拠"},
        {"科目B": "professorのB", "科目C": "エンジニアのC"},
    ]


def test_merge_refuses_an_occupation_without_expected_courses(tmp_path: Path) -> None:
    dataset, judgments, materials = judging_files(tmp_path)
    first, second = (
        {key: {"職業乙": {"土台": [{"course": course, "evidence": "根拠"}]}} for key in ROLES}
        for course in ("科目B", "科目C")
    )

    with pytest.raises(SystemExit) as stopped:
        merge(dataset, judgments, materials, *judge_outputs(tmp_path, first, second))

    assert str(stopped.value.code).startswith("期待する科目が 1 つも無い職業があります: 職業乙")


def test_merge_refuses_a_judge_that_voted_a_course_twice(tmp_path: Path) -> None:
    dataset, judgments, materials = judging_files(tmp_path)
    twice = dict(SPLIT)
    twice["student"] = {
        "職業乙": {
            "中心": [{"course": "科目C", "evidence": "根拠"}],
            "土台": [{"course": "科目C", "evidence": "根拠"}],
        }
    }

    with pytest.raises(SystemExit) as stopped:
        merge(dataset, judgments, materials, *judge_outputs(tmp_path, CORE_B, twice))

    assert "同じ科目に票が 2 つあります: 科目C" in str(stopped.value.code)


def test_nothing_is_merged_when_every_occupation_is_judged(tmp_path: Path) -> None:
    dataset, judgments, materials = judging_files(tmp_path)
    document: dict[str, Any] = read_document(dataset)
    document["occupations"].pop()
    write_document(dataset, document, DATASET_LINES)

    with pytest.raises(SystemExit) as stopped:
        merge(dataset, judgments, materials, "--first", "unused", "--second", "unused")

    assert str(stopped.value.code).startswith("判定していない職業がありません")
