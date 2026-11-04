from collections.abc import Callable

import pytest

from app.application.ports import ReasonJudgeError
from app.application.reason_judging import ReasonCase, ReasonGrade, ReasonVote
from app.presentation.cli import experiment as experiment_cli
from app.presentation.cli.evaluation_data import read_document
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
    assert "  食い違い" in lines
    assert sum(1 for line in lines if line.startswith("    r")) == 75 - 26


def test_the_check_split_shows_only_the_numbers_and_whether_the_judge_is_adopted(
    judged_by: Callable[[object], None], capsys: pytest.CaptureFixture[str]
) -> None:
    judged_by(AnsweringJudge(answer_of))

    experiment_cli.main(["reason-agreement", "--split", "check"])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("判定器と正解の一致(確かめる用 75 件")
    assert lines[1] == "  全体 κ 1.00(一致 75 / 75)"
    assert lines[-1] == "  採る条件(全体の κ 0.6 以上)を満たす"
    assert not any(line.startswith("    r") for line in lines)


def test_a_judge_that_cannot_answer_stops_with_the_reason(
    judged_by: Callable[[object], None],
) -> None:
    judged_by(FailingJudge())

    with pytest.raises(SystemExit, match="判定器が答えられませんでした.0.00 円使った.: .+: 失敗"):
        experiment_cli.main(["reason-agreement", "--split", "tune"])
