import json
from collections.abc import Callable
from dataclasses import replace

import httpx
import pytest
from pydantic import SecretStr

from app.application.judging import OVERVIEW_LENGTH
from app.application.ports import ClassificationError, CourseOdds
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse
from app.infrastructure.llm.jev_course_classifier import (
    CORE,
    CRITERIA,
    ENDPOINT,
    FOUNDATION,
    UNRELATED,
    JevCourseClassifier,
    state,
)
from tests.builders import syllabus

PROFILE = OccupationProfile("職業", "読んだ職業", None, ("甲", "乙", "丙"))
CANDIDATES = [CandidateCourse("科目A", syllabus("1")), CandidateCourse("科目B", syllabus("2"))]


def answered(probabilities: list[tuple[float, float, float]]) -> dict[str, object]:
    return {
        "model": "jev-1.14.0",
        "answers": {
            f"q{index}": {
                "type": "choice",
                "choice": CORE,
                "confidence": core,
                "probabilities": {CORE: core, FOUNDATION: foundation, UNRELATED: unrelated},
            }
            for index, (core, foundation, unrelated) in enumerate(probabilities)
        },
        "usage": {"input_tokens": 1234, "output_tokens": 9},
    }


def classifier(handle: Callable[[httpx.Request], httpx.Response]) -> JevCourseClassifier:
    client = httpx.Client(transport=httpx.MockTransport(handle))
    return JevCourseClassifier(client, SecretStr("test-key"), "jev-1.14.0")


def test_each_candidate_is_asked_the_judges_three_choices_about_one_shared_state() -> None:
    sent: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json=answered([(0.7, 0.2, 0.1), (0.1, 0.3, 0.6)]))

    classified = classifier(handle).classify(PROFILE, CANDIDATES)

    [request] = sent
    body = json.loads(request.content)
    assert str(request.url) == ENDPOINT
    assert request.headers["Authorization"] == "Bearer test-key"
    assert body["model"] == "jev-1.14.0"
    assert "職業: 読んだ職業" in body["state"]
    assert "## 科目A" in body["state"] and "## 科目B" in body["state"]
    assert list(body["questions"]) == ["q0", "q1"]
    assert body["questions"]["q1"]["type"] == "choice"
    assert "「科目B」" in body["questions"]["q1"]["instructions"]
    assert body["questions"]["q1"]["criteria"] == CRITERIA
    assert classified.odds == (
        CourseOdds("科目A", 0.7, 0.2, 0.1),
        CourseOdds("科目B", 0.1, 0.3, 0.6),
    )
    assert classified.input_tokens == 1234


def test_the_state_cuts_each_excerpt_to_what_the_judges_read() -> None:
    page = replace(syllabus("1"), overview="あ" * (OVERVIEW_LENGTH + 10))

    written = state(PROFILE, [CandidateCourse("科目A", page)])

    assert f"授業の概要と方法: {'あ' * OVERVIEW_LENGTH}\n" in written


@pytest.mark.parametrize("chances", [(0.7, 0.4, 0.1), (1.2, -0.1, -0.1), (float("nan"), 0.5, 0.5)])
def test_probabilities_outside_zero_to_one_or_not_adding_up_to_one_are_refused(
    chances: tuple[float, float, float],
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps(answered([chances, (0.1, 0.3, 0.6)])))

    with pytest.raises(ClassificationError, match="Jev の確率が 0〜1 に収まらないか") as raised:
        classifier(handle).classify(PROFILE, CANDIDATES)
    assert raised.value.input_tokens == 1234


def test_closing_the_classifier_closes_its_connections() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)))

    JevCourseClassifier(client, SecretStr("test-key"), "jev-1.14.0").close()

    assert client.is_closed


def test_an_error_status_is_reported_with_the_status_and_its_detail() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": [{"msg": "invalid"}]})

    with pytest.raises(ClassificationError, match="Jev が 422 を返しました: .*invalid"):
        classifier(handle).classify(PROFILE, CANDIDATES)


def test_an_answer_missing_a_question_cannot_be_read() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=answered([(0.7, 0.2, 0.1)]))

    with pytest.raises(ClassificationError, match="Jev の答えを読めません: KeyError") as raised:
        classifier(handle).classify(PROFILE, CANDIDATES)
    assert raised.value.input_tokens == 1234


def test_a_failed_connection_says_jev_could_not_be_called() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("接続できない", request=request)

    with pytest.raises(ClassificationError, match="Jev を呼べません: 接続できない"):
        classifier(handle).classify(PROFILE, CANDIDATES)
