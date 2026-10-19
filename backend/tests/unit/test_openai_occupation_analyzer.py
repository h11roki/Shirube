import json
from typing import Any

import pytest

from app.application.ports import OccupationAnalysisError
from app.domain.occupation import OccupationProfile
from app.infrastructure.llm.openai_occupation_analyzer import OpenAIOccupationAnalyzer
from tests.fakes import chat_answering, chat_failing


def analyzer_answering(
    message: dict[str, Any], requests: list[dict[str, Any]] | None = None
) -> OpenAIOccupationAnalyzer:
    return OpenAIOccupationAnalyzer(chat_answering(message, requests))


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
def test_missing_assumption_means_the_name_was_read_as_it_is(assumption: str | None) -> None:
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


def test_a_failed_api_call_is_an_analysis_error() -> None:
    analyzer = OpenAIOccupationAnalyzer(chat_failing(400))

    with pytest.raises(OccupationAnalysisError, match="職業: OpenAI の API 呼び出しに失敗しました"):
        analyzer.analyze("職業")
