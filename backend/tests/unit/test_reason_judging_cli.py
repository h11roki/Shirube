import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from app.application.reason_judging import sample_reasons
from app.presentation.cli.evaluation_data import (
    DEFAULT_DATASET,
    HELDOUT_DATASET,
    read_document,
    write_document,
)
from app.presentation.cli.reason_judging import (
    DEFAULT_REASON_JUDGMENTS,
    judged_from,
    main,
    reason_cases,
)
from app.presentation.cli.records import digest

RUNS = DEFAULT_DATASET.with_name("runs")


def trial(occupation: str, repeat: int = 1) -> dict[str, Any]:
    return {
        "occupation": occupation,
        "repeat": repeat,
        "interpretation": f"{occupation}の解釈",
        "assumption": "前提" if occupation.endswith("0") else None,
        "courses": [
            *(
                {
                    "name": f"柱{number}",
                    "relevance": "core",
                    "judgment": "expected",
                    "reason": f"{occupation}の柱{number}の理由",
                    "prerequisite_for": None,
                }
                for number in range(40)
            ),
            *(
                {
                    "name": f"礎{number}",
                    "relevance": "foundation",
                    "judgment": "foundation",
                    "reason": f"{occupation}の礎{number}の理由",
                    "prerequisite_for": "柱0",
                }
                for number in range(40)
            ),
        ],
    }


def run_file(tmp_path: Path, occupations: Sequence[str] = ("職業0", "職業1")) -> Path:
    path = tmp_path / "run.json"
    trials = [trial(occupation) for occupation in occupations]
    trials.append(trial(occupations[0], repeat=2))
    trials.append({"occupation": occupations[1], "repeat": 1, "failure": "失敗"})
    path.write_text(json.dumps({"trials": trials}, ensure_ascii=False), encoding="utf-8")
    return path


def vote_files(tmp_path: Path, grades: Sequence[str], count: int = 150) -> list[str]:
    paths = []
    for judge, grade in enumerate(grades, 1):
        path = tmp_path / f"judge-{judge}.json"
        votes = [
            {"id": f"r{number:03d}", "why": f"判定者{judge}の根拠", "grade": grade}
            for number in range(1, count + 1)
        ]
        path.write_text(json.dumps({"grades": votes}, ensure_ascii=False), encoding="utf-8")
        paths.append(str(path))
    return paths


def test_the_reasons_come_from_the_first_repeat_without_failed_trials(tmp_path: Path) -> None:
    cases = reason_cases(read_document(run_file(tmp_path)))

    assert len(cases) == 160
    assert {case.occupation for case in cases} == {"職業0", "職業1"}
    assert cases[0].interpretation == "職業0の解釈"
    assert cases[0].assumption == "前提"
    assert cases[40].pillar == "柱0"


def test_sample_writes_the_materials_without_telling_the_split(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["sample", str(run_file(tmp_path)), "--out", str(tmp_path / "materials")])

    materials = read_document(tmp_path / "materials" / "reasons.json")
    assert len(materials) == 150
    assert set(materials[0]) == {
        "id",
        "occupation",
        "assumption",
        "kind",
        "course",
        "pillar",
        "reason",
    }
    assert {material["kind"] for material in materials} == {"柱", "礎"}
    assert {material["occupation"] for material in materials} == {"職業0の解釈", "職業1の解釈"}
    assert capsys.readouterr().out.endswith("(整える用 75、確かめる用 75)\n")


def test_sample_refuses_a_run_with_a_heldout_occupation(tmp_path: Path) -> None:
    heldout = read_document(HELDOUT_DATASET)["occupations"][0]["name"]

    with pytest.raises(SystemExit, match="確かめ用の職業"):
        main(["sample", str(run_file(tmp_path, ("職業0", heldout))), "--out", str(tmp_path)])


def test_sample_refuses_a_run_too_small_to_sample(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"trials": [trial("職業0")]}), encoding="utf-8")

    with pytest.raises(SystemExit, match="理由を取り出せません"):
        main(["sample", str(path), "--out", str(tmp_path)])


def test_merge_writes_the_votes_and_the_middle_answer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = run_file(tmp_path)
    out = tmp_path / "reason-judgments.json"

    main(
        [
            "merge",
            str(run),
            "--votes",
            *vote_files(tmp_path, ["specific", "absent", "vague"]),
            "--out",
            str(out),
        ]
    )

    document = read_document(out)
    assert document["run"] == "run.json"
    assert document["run_fingerprint"] == digest(run.read_bytes())
    assert len(document["reasons"]) == 150
    first = document["reasons"][0]
    assert [vote["grade"] for vote in first["votes"]] == ["specific", "absent", "vague"]
    assert first["answer"] == "vague"
    assert first["split"] in {"tune", "check"}
    lines = capsys.readouterr().out.splitlines()
    assert lines[1] == "柱 76 件(3 体の一致 Fleiss の κ -0.50)"
    assert lines[2] == "  整える用: 具体的 0、ぼんやり 38、無い 0"
    assert judged_from(document, sample_reasons(reason_cases(read_document(run))))


def test_merge_refuses_an_output_missing_a_reason(tmp_path: Path) -> None:
    out = tmp_path / "reason-judgments.json"

    with pytest.raises(SystemExit, match="足りない: r150"):
        main(
            [
                "merge",
                str(run_file(tmp_path)),
                "--votes",
                *vote_files(tmp_path, ["vague"] * 3, count=149),
                "--out",
                str(out),
            ]
        )
    assert not out.exists()


def test_merge_refuses_an_unknown_grade(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="判定者の出力を読めません"):
        main(
            [
                "merge",
                str(run_file(tmp_path)),
                "--votes",
                *vote_files(tmp_path, ["vague", "vague", "great"]),
                "--out",
                str(tmp_path / "out.json"),
            ]
        )


def test_the_committed_judgments_match_the_reasons_sampled_again_from_the_run() -> None:
    document = read_document(DEFAULT_REASON_JUDGMENTS)
    run = RUNS / document["run"]

    samples = sample_reasons(reason_cases(read_document(run)), document["seed"])

    assert document["run_fingerprint"] == digest(run.read_bytes())
    assert len(judged_from(document, samples)) == 150


def test_the_committed_judgments_are_written_back_unchanged(tmp_path: Path) -> None:
    written = tmp_path / DEFAULT_REASON_JUDGMENTS.name

    write_document(written, read_document(DEFAULT_REASON_JUDGMENTS), frozenset({"votes"}))

    assert written.read_text(encoding="utf-8") == DEFAULT_REASON_JUDGMENTS.read_text(
        encoding="utf-8"
    )
