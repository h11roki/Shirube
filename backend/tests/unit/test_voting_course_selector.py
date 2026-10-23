from collections.abc import Sequence
from threading import Lock

import pytest
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.application.ports import CourseSelectionError, TokenUsage
from app.application.voting_course_selector import VotingCourseSelector
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse, CourseChoice, Relevance
from app.infrastructure.llm.openai_course_selector import OpenAICourseSelector
from app.infrastructure.llm.usage_meter import LangChainUsageMeter
from app.presentation.composition import course_selector
from app.settings import Settings
from tests.fakes import chat_answering

PROFILE = OccupationProfile("職業", "職業", None, ("甲", "乙", "丙"))
CORE = Relevance.CORE


class TakingTurns:
    def __init__(self, samples: Sequence[list[CourseChoice]]) -> None:
        self._samples = list(samples)
        self._lock = Lock()
        self.calls = 0

    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        with self._lock:
            sample = self._samples[self.calls]
            self.calls += 1
        return sample


class Failing:
    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        raise CourseSelectionError("推薦に使う外部のサービスの呼び出しに失敗しました")


class AskingChat:
    def __init__(self, chat: ChatOpenAI) -> None:
        self._chat = chat

    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        self._chat.invoke([HumanMessage("選んで")])
        return [CourseChoice("科目A", CORE, "理由A")]


def test_the_selector_is_asked_once_per_vote_and_the_majority_is_kept() -> None:
    selector = TakingTurns(
        [
            [CourseChoice("科目A", CORE, "理由A"), CourseChoice("科目B", CORE, "理由B")],
            [CourseChoice("科目A", CORE, "理由A")],
            [CourseChoice("科目A", CORE, "理由A"), CourseChoice("科目B", CORE, "理由B")],
        ]
    )

    choices = VotingCourseSelector(selector, 3).select(PROFILE, [])

    assert selector.calls == 3
    assert [choice.name for choice in choices] == ["科目A", "科目B"]


def test_a_failed_vote_fails_the_whole_selection() -> None:
    with pytest.raises(CourseSelectionError, match="外部のサービスの呼び出しに失敗"):
        VotingCourseSelector(Failing(), 3).select(PROFILE, [])


def test_the_usage_of_every_vote_is_counted_although_the_votes_run_in_threads() -> None:
    selector = AskingChat(chat_answering({"content": "はい"}))

    with LangChainUsageMeter().meter() as usage:
        VotingCourseSelector(selector, 3).select(PROFILE, [])

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
