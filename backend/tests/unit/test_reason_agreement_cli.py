import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from app.application.ports import ReasonJudgeError, ReasonJudgeUnavailableError
from app.application.reason_judging import ReasonCase, ReasonGrade, ReasonVote
from app.presentation.cli import experiment as experiment_cli
from app.presentation.cli.evaluation_data import read_document
from app.presentation.cli.experiment import REASON_CHECKS, RUNS
from app.presentation.cli.reason_judging import DEFAULT_REASON_JUDGMENTS


class AnsweringJudge:
    def __init__(self, grade_of: Callable[[ReasonCase], ReasonGrade]) -> None:
        self._grade_of = grade_of

    def judge(self, case: ReasonCase) -> ReasonVote:
        return ReasonVote(self._grade_of(case), "判定器の根拠")


class FailingJudge:
    def judge(self, case: ReasonCase) -> ReasonVote:
        raise ReasonJudgeError(f"{case.course}: 失敗")


ANSWERS = {
    (entry["occupation"], entry["course"], entry["reason"]): ReasonGrade(entry["answer"])
    for entry in read_document(DEFAULT_REASON_JUDGMENTS)["reasons"]
}


def answer_of(case: ReasonCase) -> ReasonGrade:
    return ANSWERS[(case.occupation, case.course, case.reason)]


@pytest.fixture
def judged_by(monkeypatch: pytest.MonkeyPatch) -> Callable[[object], None]:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://shirube:shirube@localhost:1/none")
    monkeypatch.setenv("REASON_JUDGE_MODEL", "gpt-5.4-nano")

    def use(judge: object) -> None:
        monkeypatch.setattr(experiment_cli, "reason_judge", lambda settings: judge)

    return use


def test_the_tune_split_shows_the_agreement_and_every_disagreement(
    judged_by: Callable[[object], None], capsys: pytest.CaptureFixture[str]
) -> None:
    judged_by(AnsweringJudge(lambda case: ReasonGrade.VAGUE))

    experiment_cli.main(["reason-agreement", "--split", "tune"])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("判定器と正解の一致(整える用 75 件、gpt-5.4-nano、指示文 ")
    assert lines[0].endswith("、0.00 円)")
    assert lines[1] == "  全体 κ 0.00(一致 26 / 75)"
    assert "    正解 ぼんやり: 具体的 0、ぼんやり 26、無い 0" in lines
    assert sum(1 for line in lines if line.startswith("    r")) == 75 - 26


def test_the_check_split_shows_only_the_numbers_and_records_its_one_use(
    judged_by: Callable[[object], None], capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    judged_by(AnsweringJudge(answer_of))
    checks = tmp_path / "checks.json"

    experiment_cli.main(["reason-agreement", "--split", "check", "--checks", str(checks)])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("判定器と正解の一致(確かめる用 75 件")
    assert lines[1] == "  全体 κ 1.00(一致 75 / 75)"
    assert lines[-1] == "  採る条件(全件を判定でき、全体の κ 0.6 以上)を満たす"
    assert not any(line.startswith("    r") for line in lines)
    [record] = read_document(checks)["checks"]
    assert record["model"] == "gpt-5.4-nano"
    assert (record["kappa"], record["agreed"], record["judged"], record["failed"]) == (
        1.0,
        75,
        75,
        0,
    )
    assert record["adopted"] is True


def test_the_check_split_refuses_a_second_use_by_the_same_judge(
    judged_by: Callable[[object], None], tmp_path: Path
) -> None:
    judged_by(AnsweringJudge(answer_of))
    checks = tmp_path / "checks.json"
    experiment_cli.main(["reason-agreement", "--split", "check", "--checks", str(checks)])
    judged_by(FailingJudge())

    with pytest.raises(
        SystemExit, match="gpt-5.4-nano、指示文 [0-9a-f]{8}.で [0-9-]+ に使いました"
    ):
        experiment_cli.main(["reason-agreement", "--split", "check", "--checks", str(checks)])
    assert len(read_document(checks)["checks"]) == 1


def test_the_committed_record_keeps_the_used_check_split_from_being_run_again(
    judged_by: Callable[[object], None], monkeypatch: pytest.MonkeyPatch
) -> None:
    [used] = read_document(REASON_CHECKS)["checks"]
    monkeypatch.setenv("REASON_JUDGE_MODEL", used["model"])
    judged_by(FailingJudge())

    with pytest.raises(SystemExit, match=f"で {used['date']} に使いました"):
        experiment_cli.main(["reason-agreement", "--split", "check"])


def test_a_judge_that_cannot_answer_is_counted_and_the_split_goes_on(
    judged_by: Callable[[object], None], capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    judged_by(FailingJudge())
    checks = tmp_path / "checks.json"

    experiment_cli.main(["reason-agreement", "--split", "check", "--checks", str(checks)])

    lines = capsys.readouterr().out.splitlines()
    assert lines[1] == "  全体 κ -(一致 0 / 0)"
    assert "  判定器が答えられなかった 75 件" in lines
    assert lines[-1].endswith("を満たさない")
    [record] = read_document(checks)["checks"]
    assert (record["kappa"], record["failed"], record["adopted"]) == (None, 75, False)


def test_the_run_can_be_given_when_it_was_moved_or_renamed(
    judged_by: Callable[[object], None], capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    moved = tmp_path / "renamed.json"
    shutil.copy(RUNS / read_document(DEFAULT_REASON_JUDGMENTS)["run"], moved)
    judged_by(AnsweringJudge(answer_of))

    experiment_cli.main(["reason-agreement", "--split", "tune", "--run", str(moved)])

    assert capsys.readouterr().out.splitlines()[1] == "  全体 κ 1.00(一致 75 / 75)"


class UnreachableJudge:
    def judge(self, case: ReasonCase) -> ReasonVote:
        raise ReasonJudgeUnavailableError("OpenAI の API 呼び出しに失敗しました")


def test_a_judge_that_cannot_be_called_stops_without_using_up_the_check_split(
    judged_by: Callable[[object], None], tmp_path: Path
) -> None:
    judged_by(UnreachableJudge())
    checks = tmp_path / "checks.json"

    with pytest.raises(SystemExit, match="判定器を呼べませんでした.+記録は残さない"):
        experiment_cli.main(["reason-agreement", "--split", "check", "--checks", str(checks)])
    assert not checks.exists()


def test_a_model_missing_from_the_price_table_is_refused_before_any_call(
    judged_by: Callable[[object], None], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REASON_JUDGE_MODEL", "unknown-model")
    judged_by(UnreachableJudge())

    with pytest.raises(SystemExit, match="料金表に無いモデルでは流しません: unknown-model"):
        experiment_cli.main(["reason-agreement", "--split", "tune"])


def test_a_broken_record_of_check_uses_is_refused(
    judged_by: Callable[[object], None], tmp_path: Path
) -> None:
    checks = tmp_path / "checks.json"
    checks.write_text('{"checks": [{"model": "gpt-5.4-nano"}]}', encoding="utf-8")
    judged_by(UnreachableJudge())

    with pytest.raises(SystemExit, match="確かめる用を使った記録を読めません"):
        experiment_cli.main(["reason-agreement", "--split", "check", "--checks", str(checks)])
