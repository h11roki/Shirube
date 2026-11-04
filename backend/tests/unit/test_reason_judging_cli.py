import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest

from app.presentation.cli import reason_judging
from app.presentation.cli.evaluation_data import HELDOUT_DATASET, read_document, write_document
from app.presentation.cli.experiment import RUNS
from app.presentation.cli.reason_judging import (
    DEFAULT_REASON_JUDGMENTS,
    VOTE_LINES,
    main,
    reason_cases,
)

MODEL = "判定者のモデル"


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


def run_file(
    tmp_path: Path, occupations: Sequence[str] = ("職業0", "職業1"), failed: str | None = None
) -> Path:
    path = tmp_path / "run.json"
    trials = [trial(occupation) for occupation in occupations]
    trials.append(trial(occupations[0], repeat=2))
    trials.append({"occupation": failed or occupations[1], "repeat": 1, "failure": "失敗"})
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


def merge(tmp_path: Path, run: Path, votes: Sequence[str]) -> Path:
    out = tmp_path / "out.json"
    main(
        [
            "merge",
            str(run),
            "--materials",
            str(tmp_path / "materials"),
            "--votes",
            *votes,
            "--model",
            MODEL,
            "--out",
            str(out),
        ]
    )
    return out


def sampled_run(tmp_path: Path) -> Path:
    run = run_file(tmp_path)
    main(["sample", str(run), "--out", str(tmp_path / "materials")])
    return run


def merged(tmp_path: Path, grades: Sequence[str] = ("specific", "vague", "vague")) -> Path:
    return merge(tmp_path, sampled_run(tmp_path), vote_files(tmp_path, grades))


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
    sampled_run(tmp_path)

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


@pytest.mark.parametrize("in_failed_trial", [False, True], ids=["reasons", "failed-trial"])
def test_sample_refuses_a_run_with_a_heldout_occupation_anywhere(
    tmp_path: Path, in_failed_trial: bool
) -> None:
    heldout = read_document(HELDOUT_DATASET)["occupations"][0]["name"]
    run = (
        run_file(tmp_path, failed=heldout)
        if in_failed_trial
        else run_file(tmp_path, ("職業0", heldout))
    )

    with pytest.raises(SystemExit, match="確かめ用の職業"):
        main(["sample", str(run), "--out", str(tmp_path)])


def test_sample_refuses_a_run_too_small_to_sample(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"trials": [trial("職業0")]}), encoding="utf-8")

    with pytest.raises(SystemExit, match="理由を取り出せません"):
        main(["sample", str(path), "--out", str(tmp_path)])


def test_merge_writes_the_votes_and_the_middle_answer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = sampled_run(tmp_path)
    capsys.readouterr()

    document = read_document(
        merge(tmp_path, run, vote_files(tmp_path, ["specific", "absent", "vague"]))
    )

    assert document["run"] == "run.json"
    assert document["model"] == MODEL
    assert len(document["reasons"]) == 150
    first = document["reasons"][0]
    assert [vote["grade"] for vote in first["votes"]] == ["specific", "absent", "vague"]
    assert first["answer"] == "vague"
    assert first["split"] in {"tune", "check"}
    assert first["interpretation"] == f"{first['occupation']}の解釈"
    lines = capsys.readouterr().out.splitlines()
    assert lines[1] == "柱 76 件: 具体的 0、ぼんやり 76、無い 0(3 体の一致 Fleiss の κ -0.50)"
    assert lines[2] == "礎 74 件: 具体的 0、ぼんやり 74、無い 0(3 体の一致 Fleiss の κ -0.50)"


def test_merge_refuses_votes_on_materials_sampled_from_another_run(tmp_path: Path) -> None:
    sampled_run(tmp_path)
    other = tmp_path / "other"
    other.mkdir()

    with pytest.raises(
        SystemExit, match="判定者に渡した資料が、この結果から取り直した理由と違います"
    ):
        merge(tmp_path, run_file(other, ("職業2", "職業3")), vote_files(tmp_path, ["vague"] * 3))
    assert not (tmp_path / "out.json").exists()


def test_merge_refuses_an_output_missing_a_reason(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="足りない: r150"):
        merge(tmp_path, sampled_run(tmp_path), vote_files(tmp_path, ["vague"] * 3, count=149))
    assert not (tmp_path / "out.json").exists()


def test_merge_refuses_an_unknown_grade(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="決まりに合いません: 段は absent、vague、specific"):
        merge(tmp_path, sampled_run(tmp_path), vote_files(tmp_path, ["vague", "vague", "great"]))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [("grade", ["vague"], "段は absent"), ("why", ["根拠"], "根拠は文字列")],
    ids=["grade", "why"],
)
def test_merge_refuses_a_vote_that_is_not_text(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    run = sampled_run(tmp_path)
    votes = vote_files(tmp_path, ["vague"] * 3)
    broken = read_document(Path(votes[2]))
    broken["grades"][0][field] = value
    Path(votes[2]).write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SystemExit, match=f"決まりに合いません: {message}"):
        merge(tmp_path, run, votes)


def test_merge_refuses_the_same_judge_output_passed_three_times(tmp_path: Path) -> None:
    run = sampled_run(tmp_path)
    once = vote_files(tmp_path, ["vague"])[0]

    with pytest.raises(SystemExit, match="同じ判定者の出力が 2 つ以上"):
        merge(tmp_path, run, [once] * 3)


def test_the_instructions_fingerprint_follows_only_the_instructions_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompt = tmp_path / "prompt.md"
    monkeypatch.setattr(reason_judging, "PROMPT", prompt)

    def fingerprint(text: str) -> str:
        prompt.write_text(text, encoding="utf-8")
        return reason_judging.instructions_fingerprint()

    base = fingerprint("# 題\n\n使い方\n\n## 指示文\n\n判定の決まり\n")

    assert fingerprint("# 題\n\n直した使い方\n\n## 指示文\n\n判定の決まり\n") == base
    assert fingerprint("# 題\n\n使い方\n\n## 指示文\n\n直した判定の決まり\n") != base
    with pytest.raises(ValueError, match="「指示文」の節がありません"):
        fingerprint("# 題\n\n使い方\n")


def test_merge_needs_the_place_to_write_so_it_never_overwrites_the_committed_answers(
    tmp_path: Path,
) -> None:
    run = sampled_run(tmp_path)
    votes = vote_files(tmp_path, ["vague"] * 3)

    with pytest.raises(SystemExit) as stopped:
        main(
            [
                "merge",
                str(run),
                "--materials",
                str(tmp_path / "materials"),
                "--votes",
                *votes,
                "--model",
                MODEL,
            ]
        )

    assert stopped.value.code == 2


def test_check_prints_the_answers_of_judgments_that_match_the_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = merged(tmp_path)
    capsys.readouterr()

    main(["check", str(tmp_path / "run.json"), "--judgments", str(out)])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"{out} は run.json の理由と合う"
    assert lines[1].startswith("柱 76 件: 具体的 0、ぼんやり 76、無い 0")


def test_check_refuses_judgments_made_from_another_version_of_the_run(tmp_path: Path) -> None:
    out = merged(tmp_path)
    run = tmp_path / "run.json"
    run.write_text(run.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="違うもとから作っています: run_fingerprint"):
        main(["check", str(run), "--judgments", str(out)])


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda document: document.update(repeat=2), "違うもとから作っています: repeat"),
        (
            lambda document: document.update(prompt_fingerprint="00000000"),
            "違うもとから作っています: prompt_fingerprint",
        ),
        (lambda document: document["reasons"].reverse(), "同じ順に並んでいません"),
        (
            lambda document: document["reasons"][0].update(reason="書き換えた理由"),
            "取り直した理由と違います",
        ),
        (
            lambda document: document["reasons"][0].update(answer="specific"),
            "3 票の中央値ではありません",
        ),
        (
            lambda document: document["reasons"][0].pop("interpretation"),
            "正解か判定者の指示文を読めません",
        ),
        (
            lambda document: document["reasons"][0]["votes"].pop(),
            "正解の票が決まりに合いません",
        ),
    ],
    ids=[
        "repeat",
        "prompt",
        "reordered",
        "reason-edited",
        "answer-edited",
        "older-format",
        "two-votes",
    ],
)
def test_check_refuses_judgments_that_drifted_from_the_run(
    tmp_path: Path, change: Callable[[dict[str, Any]], object], message: str
) -> None:
    out = merged(tmp_path)
    document = read_document(out)
    change(document)
    write_document(out, document, VOTE_LINES)

    with pytest.raises(SystemExit, match=message):
        main(["check", str(tmp_path / "run.json"), "--judgments", str(out)])


def test_the_committed_judgments_match_the_reasons_sampled_again_from_the_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = RUNS / read_document(DEFAULT_REASON_JUDGMENTS)["run"]

    main(["check", str(run)])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].endswith(f"は {run.name} の理由と合う")
    assert lines[1].startswith("柱 76 件")
    assert lines[2].startswith("礎 74 件")


def test_the_committed_judgments_are_written_back_unchanged(tmp_path: Path) -> None:
    written = tmp_path / DEFAULT_REASON_JUDGMENTS.name

    write_document(written, read_document(DEFAULT_REASON_JUDGMENTS), VOTE_LINES)

    assert written.read_text(encoding="utf-8") == DEFAULT_REASON_JUDGMENTS.read_text(
        encoding="utf-8"
    )


def test_compare_puts_the_two_sides_side_by_side_with_an_interval(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before_dir, after_dir = tmp_path / "before", tmp_path / "after"
    before_dir.mkdir()
    after_dir.mkdir()
    before = merged(before_dir, ("vague", "vague", "vague"))
    after = merged(after_dir, ("specific", "specific", "vague"))
    capsys.readouterr()

    main(
        [
            "compare",
            "--before",
            str(before_dir / "run.json"),
            str(before),
            "--after",
            str(after_dir / "run.json"),
            str(after),
        ]
    )

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "理由の文の比べ(前 run.json、後 run.json)"
    assert lines[1] == "  柱 76 件 → 76 件"
    assert lines[2] == (
        "    具体的 0(0.0%) → 76(100.0%)、+100.0 ポイント(95% 区間 +100.0〜+100.0、差あり)"
    )
    assert lines[3] == (
        "    ぼんやり 76(100.0%) → 0(0.0%)、-100.0 ポイント(95% 区間 -100.0〜-100.0、差あり)"
    )
    assert lines[5] == "  礎 74 件 → 74 件"
    assert lines[-1] == "  80 字を超える理由: 前 0 / 160(0.0%)、後 0 / 160(0.0%)"


def test_compare_refuses_the_same_run_on_both_sides(tmp_path: Path) -> None:
    out = merged(tmp_path)
    run = str(tmp_path / "run.json")

    with pytest.raises(SystemExit, match="同じ実験の結果"):
        main(["compare", "--before", run, str(out), "--after", run, str(out)])
