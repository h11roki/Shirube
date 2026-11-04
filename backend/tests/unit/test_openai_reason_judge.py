import json
from typing import Any

import pytest

from app.application.ports import ReasonJudgeError, ReasonJudgeUnavailableError
from app.application.reason_judging import ReasonCase, ReasonGrade, ReasonVote
from app.domain.recommendation import Relevance
from app.infrastructure.llm.openai_reason_judge import INSTRUCTIONS, OpenAIReasonJudge
from tests.fakes import chat_answering, chat_failing

CORE = ReasonCase("職業名", "解釈した職業", None, Relevance.CORE, "授業A", None, "柱の理由")
FOUNDATION = ReasonCase(
    "職業名", "解釈した職業", "前提の文", Relevance.FOUNDATION, "授業B", "授業A", "礎の理由"
)


def verdict(why: str, grade: str) -> dict[str, Any]:
    return {
        "content": json.dumps({"quote": "", "why": why, "grade": grade}, ensure_ascii=False),
        "refusal": None,
    }


def test_the_verdict_becomes_a_vote_and_the_reason_is_sent_with_what_the_judges_saw() -> None:
    requests: list[dict[str, Any]] = []
    judge = OpenAIReasonJudge(chat_answering(verdict(" 仕事に結び付く ", "specific"), requests))

    vote = judge.judge(FOUNDATION)

    assert vote == ReasonVote(ReasonGrade.SPECIFIC, "仕事に結び付く")
    [request] = requests
    system, user = request["messages"]
    assert system["content"] == INSTRUCTIONS
    assert user["content"] == (
        "職業: 解釈した職業\n"
        "職業の解釈の前提: 前提の文\n"
        "種類: 礎\n"
        "授業: 授業B\n"
        "つながる柱: 授業A\n"
        "理由: 礎の理由"
    )
    schema = request["response_format"]["json_schema"]["schema"]
    assert list(schema["properties"]) == ["quote", "why", "grade"]
    assert schema["properties"]["grade"]["enum"] == ["specific", "vague", "absent"]


def test_a_pillar_reason_is_sent_without_an_assumption_or_a_pillar_to_lead_to() -> None:
    requests: list[dict[str, Any]] = []
    judge = OpenAIReasonJudge(chat_answering(verdict("根拠", "vague"), requests))

    judge.judge(CORE)

    user = requests[0]["messages"][1]["content"]
    assert user == "職業: 解釈した職業\n種類: 柱\n授業: 授業A\n理由: 柱の理由"


def test_a_long_evidence_is_cut_to_the_length_the_answers_keep() -> None:
    judge = OpenAIReasonJudge(chat_answering(verdict("あ" * 80, "absent")))

    assert judge.judge(CORE).why == "あ" * 60


def test_an_empty_evidence_keeps_the_grade() -> None:
    judge = OpenAIReasonJudge(chat_answering(verdict("  ", "vague")))

    assert judge.judge(CORE) == ReasonVote(ReasonGrade.VAGUE, "根拠なし")


@pytest.mark.parametrize(
    "message",
    [verdict("根拠", "great"), {"content": "not json", "refusal": None}],
    ids=["unknown-grade", "broken"],
)
def test_an_unusable_answer_is_a_judge_error(message: dict[str, Any]) -> None:
    judge = OpenAIReasonJudge(chat_answering(message))

    with pytest.raises(ReasonJudgeError, match="職業名 の 授業A: LLM の答えを使えません"):
        judge.judge(CORE)


def test_a_request_the_api_rejects_is_an_error_of_that_reason_only() -> None:
    judge = OpenAIReasonJudge(chat_failing(400))

    with pytest.raises(ReasonJudgeError, match="職業名 の 授業A: LLM の答えを使えません"):
        judge.judge(CORE)


def test_a_failed_api_call_tells_that_the_judge_could_not_be_called() -> None:
    judge = OpenAIReasonJudge(chat_failing(401))

    with pytest.raises(ReasonJudgeUnavailableError, match="OpenAI の API 呼び出しに失敗しました"):
        judge.judge(CORE)
