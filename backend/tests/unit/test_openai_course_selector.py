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
from tests.fakes import chat_answering, chat_failing

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


def answer(
    core: list[dict[str, str]] | None = None, foundation: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    body = {"core": core or [], "foundation": foundation or []}
    return {"content": json.dumps(body, ensure_ascii=False), "refusal": None}


def test_answer_becomes_choices_and_names_are_limited_to_the_candidates() -> None:
    requests: list[dict[str, Any]] = []
    selector = selector_answering(
        answer(
            core=[{"name": "科目B", "reason": " 理由B "}],
            foundation=[{"name": "科目A", "prerequisite_for": "科目B", "reason": "理由A"}],
        ),
        requests,
    )

    choices = selector.select(PROFILE, CANDIDATES)

    assert choices == [
        CourseChoice("科目B", Relevance.CORE, "理由B"),
        CourseChoice("科目A", Relevance.FOUNDATION, "理由A", "科目B"),
    ]
    [request] = requests
    schema = request["response_format"]["json_schema"]
    assert schema["strict"] is True
    groups = schema["schema"]["properties"]
    assert list(groups) == ["core", "foundation"]
    core = groups["core"]["items"]["properties"]
    foundation = groups["foundation"]["items"]["properties"]
    assert core["name"]["enum"] == ["科目A", "科目B"]
    assert list(foundation) == ["name", "prerequisite_for", "reason"]
    assert (
        foundation["name"]["enum"] == foundation["prerequisite_for"]["enum"] == ["科目A", "科目B"]
    )


def test_foundations_for_courses_not_chosen_as_core_are_left_to_arrange() -> None:
    selector = selector_answering(
        answer(foundation=[{"name": "科目A", "prerequisite_for": "科目B", "reason": "理由A"}])
    )

    assert selector.select(PROFILE, CANDIDATES) == [
        CourseChoice("科目A", Relevance.FOUNDATION, "理由A", "科目B")
    ]


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
        answer(foundation=[{"name": "科目A", "reason": "理由"}]),
        answer(core=[{"name": "科目A", "reason": " "}]),
        {"content": json.dumps({"courses": []}), "refusal": None},
    ],
    ids=[
        "refusal",
        "broken-json",
        "no-content",
        "foundation-without-prerequisite",
        "blank-reason",
        "old-shape",
    ],
)
def test_refused_or_unusable_answers_are_selection_errors(message: dict[str, Any]) -> None:
    with pytest.raises(CourseSelectionError, match="職業: LLM の答えを使えません"):
        selector_answering(message).select(PROFILE, CANDIDATES)


def test_an_answer_cut_off_by_the_length_limit_is_an_unusable_answer() -> None:
    selector = OpenAICourseSelector(chat_answering(answer(), finish_reason="length"))

    with pytest.raises(CourseSelectionError, match="職業: LLM の答えを使えません"):
        selector.select(PROFILE, CANDIDATES)


def test_a_failed_api_call_is_a_selection_error() -> None:
    selector = OpenAICourseSelector(chat_failing(400))

    with pytest.raises(CourseSelectionError, match="職業: OpenAI の API 呼び出しに失敗しました"):
        selector.select(PROFILE, CANDIDATES)
