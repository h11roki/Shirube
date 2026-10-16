import json
from typing import Any

import httpx
import pytest
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.application.ports import OccupationAnalysisError
from app.domain.occupation import OccupationProfile
from app.infrastructure.llm.openai_occupation_analyzer import OpenAIOccupationAnalyzer


def analyzer_answering(
    message: dict[str, Any], requests: list[dict[str, Any]] | None = None
) -> OpenAIOccupationAnalyzer:
    def respond(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", **message},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    return OpenAIOccupationAnalyzer(
        ChatOpenAI(model="test-model", api_key=SecretStr("test-key"), http_client=client)
    )


def answer(**fields: Any) -> dict[str, Any]:
    return {"content": json.dumps(fields, ensure_ascii=False), "refusal": None}


def test_structured_answer_becomes_a_profile_and_the_schema_limits_the_skills() -> None:
    requests: list[dict[str, Any]] = []
    analyzer = analyzer_answering(
        answer(
            interpretation="IT コンサルタント",
            assumption="情報系の学生に多い IT コンサルタントと解釈した",
            skills=["業務分析", "要件定義", "システム設計"],
        ),
        requests,
    )

    profile = analyzer.analyze("コンサルタント")

    assert profile == OccupationProfile(
        "コンサルタント",
        "IT コンサルタント",
        "情報系の学生に多い IT コンサルタントと解釈した",
        ("業務分析", "要件定義", "システム設計"),
    )
    [request] = requests
    assert request["messages"][-1] == {"role": "user", "content": "コンサルタント"}
    response_format = request["response_format"]["json_schema"]
    assert response_format["strict"] is True
    skills = response_format["schema"]["properties"]["skills"]
    assert (skills["minItems"], skills["maxItems"]) == (3, 6)


@pytest.mark.parametrize("assumption", [None, "", "  "], ids=["null", "empty", "blank"])
def test_missing_assumption_means_the_name_was_not_ambiguous(assumption: str | None) -> None:
    analyzer = analyzer_answering(
        answer(interpretation="制御エンジニア", assumption=assumption, skills=["甲", "乙", "丙"])
    )

    assert analyzer.analyze("制御エンジニア").assumption is None


def test_surrounding_spaces_in_the_answer_are_trimmed() -> None:
    analyzer = analyzer_answering(
        answer(
            interpretation=" 制御エンジニア ",
            assumption=None,
            skills=[" 制御工学", "信号処理 ", "C 言語"],
        )
    )

    profile = analyzer.analyze("制御エンジニア")

    assert (profile.interpretation, profile.skills) == (
        "制御エンジニア",
        ("制御工学", "信号処理", "C 言語"),
    )


@pytest.mark.parametrize(
    "message",
    [
        {"content": None, "refusal": "答えられません"},
        answer(interpretation="職業", assumption=None, skills=list("甲乙丙丁戊己庚")),
        {"content": "{not json", "refusal": None},
        {"content": None, "refusal": None},
        answer(interpretation="職業", assumption=None, skills=["甲", "乙", "甲"]),
    ],
    ids=["refusal", "seven-skills", "broken-json", "no-content", "duplicated-skill"],
)
def test_refused_or_unusable_answers_are_analysis_errors(message: dict[str, Any]) -> None:
    with pytest.raises(OccupationAnalysisError, match="職業: LLM の答えを使えません"):
        analyzer_answering(message).analyze("職業")
