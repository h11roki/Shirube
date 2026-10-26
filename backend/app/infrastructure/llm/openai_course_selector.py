from typing import Any, Self

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRefusalError
from openai import ContentFilterFinishReasonError, LengthFinishReasonError, OpenAIError
from pydantic import BaseModel, SecretStr

from app.application.ports import CourseSelectionError
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse, CourseChoice, Relevance

OVERVIEW_LIMIT = 450
OBJECTIVES_LIMIT = 250
SCHEDULE_LIMIT = 350
REASON_LIMIT = 80

INSTRUCTIONS = f"""\
あなたは大学の理工系学部の学生に、なりたい職業に向けた履修を助ける進路アドバイザーです。
職業と必要なスキル、候補の授業のシラバスの抜粋を読み、\
候補の授業から core(中心)と foundation(土台)の授業を選んでください。\
科目名だけで決めず、抜粋の中身で判断します。

- core(中心): 授業の中心テーマが、その職業の仕事で直接使う知識・技能そのもの
- foundation(土台): core に選んだ授業の内容を学ぶ前提として必要な基礎\
(その core の授業で使う数学、物理、回路、プログラミングの基礎など)

先に core を全て選び、そのあと foundation を選びます。\
foundation には、その授業を前提にする core の授業を 1 つ prerequisite_for に書きます。\
core に選んだどの授業の前提にもならない授業は foundation にしません。\
core か foundation か迷った授業は、\
前提にする core の授業があれば foundation、無ければ core にします。\
どちらでもない授業と、選ぶか迷った授業は答えに含めません。\
数の目安や上限はなく、職業に関係する授業が少なければ、少なく選んで構いません。

理由には、その職業を目指す学生がなぜ取るべきかを、抜粋の中身に基づいて自分の言葉で \
{REASON_LIMIT} 字以内で書きます。\
foundation の理由には、prerequisite_for の授業のどの内容の前提になるかを、\
両方の授業の抜粋に基づいて書きます。\
抜粋の文をそのまま写さず、抜粋に書いていないことは書きません。\
理由は学生が読む文なので、core、foundation、prerequisite_for などの英語の語を書かず、\
授業は科目名で書きます。"""


def _excerpt(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit]


def _request(profile: OccupationProfile, candidates: list[CandidateCourse]) -> str:
    lines = [f"職業: {profile.interpretation}"]
    if profile.assumption is not None:
        lines.append(f"前提: {profile.assumption}")
    lines += [f"必要なスキル: {'、'.join(profile.skills)}", "", "候補の授業:"]
    for candidate in candidates:
        page = candidate.syllabus
        themes = "、".join(session.theme for session in page.sessions if session.theme.strip())
        lines += [
            "",
            f"## {candidate.name}",
            f"授業の概要と方法: {_excerpt(page.overview, OVERVIEW_LIMIT)}",
            f"到達目標: {_excerpt(page.objectives, OBJECTIVES_LIMIT)}",
            f"各回のテーマ: {_excerpt(themes, SCHEDULE_LIMIT)}",
        ]
    return "\n".join(lines)


def _schema(names: list[str]) -> dict[str, Any]:
    core = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "enum": names, "description": "core に選んだ授業の科目名"},
            "reason": {"type": "string", "description": f"取るべき理由。{REASON_LIMIT} 字以内"},
        },
        "required": ["name", "reason"],
        "additionalProperties": False,
    }
    foundation = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "enum": names,
                "description": "foundation に選んだ授業の科目名",
            },
            "prerequisite_for": {
                "type": "string",
                "enum": names,
                "description": "この授業を前提にする、core に選んだ授業の科目名",
            },
            "reason": {
                "type": "string",
                "description": "取るべき理由。prerequisite_for の授業のどの内容の"
                f"前提になるかを書く。{REASON_LIMIT} 字以内",
            },
        },
        "required": ["name", "prerequisite_for", "reason"],
        "additionalProperties": False,
    }
    return {
        "title": "CourseSelection",
        "type": "object",
        "properties": {
            "core": {"type": "array", "items": core},
            "foundation": {"type": "array", "items": foundation},
        },
        "required": ["core", "foundation"],
        "additionalProperties": False,
    }


class _Core(BaseModel):
    name: str
    reason: str


class _Foundation(BaseModel):
    name: str
    prerequisite_for: str
    reason: str


class _Selection(BaseModel):
    core: list[_Core]
    foundation: list[_Foundation]


class OpenAICourseSelector:
    def __init__(self, chat: ChatOpenAI, instructions: str = INSTRUCTIONS) -> None:
        self._chat = chat
        self._instructions = instructions

    @classmethod
    def connect(
        cls, model: str, api_key: SecretStr, timeout: float, retries: int, instructions: str
    ) -> Self:
        chat = ChatOpenAI(model=model, api_key=api_key, timeout=timeout, max_retries=retries)
        return cls(chat, instructions)

    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        client = self._chat.with_structured_output(
            _schema([candidate.name for candidate in candidates]), method="json_schema", strict=True
        )
        messages = [SystemMessage(self._instructions), HumanMessage(_request(profile, candidates))]
        try:
            selection = _Selection.model_validate(client.invoke(messages))
            return [
                CourseChoice(choice.name, Relevance.CORE, choice.reason.strip())
                for choice in selection.core
            ] + [
                CourseChoice(
                    choice.name,
                    Relevance.FOUNDATION,
                    choice.reason.strip(),
                    choice.prerequisite_for,
                )
                for choice in selection.foundation
            ]
        except (
            OpenAIRefusalError,
            ContentFilterFinishReasonError,
            LengthFinishReasonError,
            ValueError,
        ) as error:
            message = f"{profile.occupation}: LLM の答えを使えません: {error}"
            raise CourseSelectionError(message) from error
        except OpenAIError as error:
            message = f"{profile.occupation}: OpenAI の API 呼び出しに失敗しました: {error}"
            raise CourseSelectionError(message) from error
