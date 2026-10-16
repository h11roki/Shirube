import json
from dataclasses import replace
from typing import Any

import pytest

from app.application.ports import CourseSelectionError
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse, CourseChoice, Relevance
from app.domain.syllabus import Session
from app.infrastructure.llm.openai_course_selector import OpenAICourseSelector
from tests.builders import syllabus
from tests.fakes import chat_answering

PROFILE = OccupationProfile("職業", "解釈した職業", "前提の文", ("甲", "乙", "丙"))
CANDIDATES = [
    CandidateCourse(
        "科目A",
        replace(
            syllabus("10000"),
            overview="概要" * 300,
            objectives="目標\n\n  の文",
            sessions=(Session("1", "導入", ""), Session("2", "  ", ""), Session("3", "応用", "")),
        ),
    ),
    CandidateCourse("科目B", syllabus("10001")),
]


def selector_answering(
    message: dict[str, Any], requests: list[dict[str, Any]] | None = None
) -> OpenAICourseSelector:
    return OpenAICourseSelector(chat_answering(message, requests))


def answer(*courses: dict[str, str]) -> dict[str, Any]:
    return {"content": json.dumps({"courses": list(courses)}, ensure_ascii=False), "refusal": None}


def test_answer_becomes_choices_and_names_are_limited_to_the_candidates() -> None:
    requests: list[dict[str, Any]] = []
    selector = selector_answering(
        answer(
            {"name": "科目B", "relevance": "core", "reason": " 理由B "},
            {"name": "科目A", "relevance": "foundation", "reason": "理由A"},
        ),
        requests,
    )

    choices = selector.select(PROFILE, CANDIDATES)

    assert choices == [
        CourseChoice("科目B", Relevance.CORE, "理由B"),
        CourseChoice("科目A", Relevance.FOUNDATION, "理由A"),
    ]
    [request] = requests
    schema = request["response_format"]["json_schema"]
    assert schema["strict"] is True
    item = schema["schema"]["properties"]["courses"]["items"]["properties"]
    assert item["name"]["enum"] == ["科目A", "科目B"]
    assert item["relevance"]["enum"] == ["core", "foundation"]


def test_request_shows_the_profile_and_trimmed_excerpts() -> None:
    requests: list[dict[str, Any]] = []
    selector_answering(answer(), requests).select(PROFILE, CANDIDATES)

    content = requests[0]["messages"][-1]["content"]
    assert content.startswith("職業: 解釈した職業\n前提: 前提の文\n必要なスキル: 甲、乙、丙\n")
    assert f"授業の概要と方法: {'概要' * 225}\n" in content
    assert "到達目標: 目標 の文\n" in content
    assert "各回のテーマ: 導入、応用\n" in content
    assert "## 科目B" in content


@pytest.mark.parametrize(
    "message",
    [
        {"content": None, "refusal": "答えられません"},
        {"content": "{not json", "refusal": None},
        {"content": None, "refusal": None},
        answer({"name": "科目A", "relevance": "maybe", "reason": "理由"}),
        answer({"name": "科目A", "relevance": "core", "reason": " "}),
        {"content": json.dumps({"choices": []}), "refusal": None},
    ],
    ids=["refusal", "broken-json", "no-content", "unknown-relevance", "blank-reason", "wrong-key"],
)
def test_refused_or_unusable_answers_are_selection_errors(message: dict[str, Any]) -> None:
    with pytest.raises(CourseSelectionError, match="職業: LLM の答えを使えません"):
        selector_answering(message).select(PROFILE, CANDIDATES)
