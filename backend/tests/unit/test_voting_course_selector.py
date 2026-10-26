import json
from collections.abc import Sequence
from threading import Event, Lock

import pytest
from pydantic import SecretStr

from app.application.ports import CourseSelectionError, TokenUsage
from app.application.voting_course_selector import VotingCourseSelector
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse, CourseChoice, Relevance
from app.infrastructure.llm.openai_course_selector import INSTRUCTIONS, OpenAICourseSelector
from app.infrastructure.llm.usage_meter import LangChainUsageMeter
from app.presentation.composition import course_selector
from app.settings import Settings
from tests.builders import syllabus
from tests.fakes import chat_answering

PROFILE = OccupationProfile("職業", "職業", None, ("甲", "乙", "丙"))
CORE = Relevance.CORE
UPSTREAM = CourseSelectionError("推薦に使う外部のサービスの呼び出しに失敗しました")


class TakingTurns:
    def __init__(self, answers: Sequence[list[CourseChoice] | Exception]) -> None:
        self._answers = list(answers)
        self._lock = Lock()
        self.calls = 0

    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        with self._lock:
            answer = self._answers[self.calls]
            self.calls += 1
        if isinstance(answer, Exception):
            raise answer
        return answer


def test_the_selector_is_asked_once_per_vote_and_the_majority_is_kept() -> None:
    selector = TakingTurns(
        [
            [CourseChoice("科目A", CORE, "理由A"), CourseChoice("科目B", CORE, "理由B")],
            [CourseChoice("科目A", CORE, "理由A")],
            [CourseChoice("科目A", CORE, "理由A"), CourseChoice("科目B", CORE, "理由B")],
        ]
    )

    choices = VotingCourseSelector(selector, 3, 0).select(PROFILE, [])

    assert selector.calls == 3
    assert [choice.name for choice in choices] == ["科目A", "科目B"]


def test_one_failed_vote_fails_the_whole_selection_after_every_vote_answered() -> None:
    answer = [CourseChoice("科目A", CORE, "理由A")]
    selector = TakingTurns([answer, UPSTREAM, answer])

    with pytest.raises(CourseSelectionError, match="外部のサービスの呼び出しに失敗"):
        VotingCourseSelector(selector, 3, 0).select(PROFILE, [])

    assert selector.calls == 3


def test_one_failure_is_raised_and_the_other_failed_votes_are_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    selector = TakingTurns(
        [
            CourseSelectionError("一つ目の失敗"),
            CourseSelectionError("二つ目の失敗"),
            [CourseChoice("科目A", CORE, "理由")],
        ]
    )

    with pytest.raises(CourseSelectionError) as raised:
        VotingCourseSelector(selector, 3, 0).select(PROFILE, [])

    other = "二つ目の失敗" if str(raised.value) == "一つ目の失敗" else "一つ目の失敗"
    assert other in caplog.text


def test_the_later_votes_are_sent_after_the_wait_so_the_first_prompt_can_be_cached() -> None:
    events: list[str] = []
    first_asked = Event()

    class Recording:
        def select(
            self, profile: OccupationProfile, candidates: list[CandidateCourse]
        ) -> list[CourseChoice]:
            events.append("vote")
            first_asked.set()
            return []

    def wait(seconds: float) -> None:
        first_asked.wait(timeout=5)
        events.append(f"wait {seconds}")

    VotingCourseSelector(Recording(), 3, 0.5, wait).select(PROFILE, [])

    assert events == ["vote", "wait 0.5", "vote", "vote"]


def test_the_usage_of_every_vote_is_counted_although_the_votes_run_in_threads() -> None:
    answer = {"core": [{"name": "科目A", "reason": "理由A"}], "foundation": []}
    selector = OpenAICourseSelector(
        chat_answering({"content": json.dumps(answer, ensure_ascii=False), "refusal": None}),
        INSTRUCTIONS,
    )

    with LangChainUsageMeter().meter() as usage:
        choices = VotingCourseSelector(selector, 3, 0).select(
            PROFILE, [CandidateCourse("科目A", syllabus("10000"))]
        )

    assert choices == [CourseChoice("科目A", CORE, "理由A")]
    assert usage() == {"test-model": TokenUsage(input=3, cached=0, output=3)}


@pytest.mark.parametrize(
    ("votes", "kind"),
    [(1, OpenAICourseSelector), (3, VotingCourseSelector)],
    ids=["single", "votes"],
)
def test_the_selection_votes_only_when_more_than_one_vote_is_set(votes: int, kind: type) -> None:
    settings = Settings(
        database_url="postgresql+psycopg://shirube@localhost/shirube",
        openai_api_key=SecretStr("test-key"),
        selection_votes=votes,
    )

    assert isinstance(course_selector(settings), kind)
