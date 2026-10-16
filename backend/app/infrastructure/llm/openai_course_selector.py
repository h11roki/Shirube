from typing import Any, Self

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRefusalError
from pydantic import SecretStr

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
候補の授業それぞれを次の 3 つに分けてください。\
科目名だけで決めず、抜粋の中身で判断します。

- core(中心): 授業の中心テーマが、その職業の仕事で直接使う知識・技能そのもの
- foundation(土台): 中心の授業を学ぶための基礎(数学、物理、基礎回路、プログラミングの基礎など)、\
または授業の一部の回でその知識に触れる
- 関係なし: それ以外

中心か土台か迷ったら土台にします。数の目安や上限はありません。関係なしの授業は答えに含めません。

中心と土台の授業には、その職業を目指す学生がなぜ取るべきかを、抜粋の中身に基づいて自分の言葉で \
{REASON_LIMIT} 字以内で書きます。抜粋の文をそのまま写さず、抜粋に書いていないことは書きません。"""


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
    choice = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "enum": names, "description": "候補の授業の科目名"},
            "relevance": {"type": "string", "enum": [relevance.value for relevance in Relevance]},
            "reason": {"type": "string", "description": f"取るべき理由。{REASON_LIMIT} 字以内"},
        },
        "required": ["name", "relevance", "reason"],
        "additionalProperties": False,
    }
    return {
        "title": "CourseSelection",
        "type": "object",
        "properties": {"courses": {"type": "array", "items": choice}},
        "required": ["courses"],
        "additionalProperties": False,
    }


class OpenAICourseSelector:
    def __init__(self, chat: ChatOpenAI) -> None:
        self._chat = chat

    @classmethod
    def connect(cls, model: str, api_key: SecretStr) -> Self:
        return cls(ChatOpenAI(model=model, api_key=api_key))

    def select(
        self, profile: OccupationProfile, candidates: list[CandidateCourse]
    ) -> list[CourseChoice]:
        client = self._chat.with_structured_output(
            _schema([candidate.name for candidate in candidates]), method="json_schema", strict=True
        )
        messages = [SystemMessage(INSTRUCTIONS), HumanMessage(_request(profile, candidates))]
        try:
            output = client.invoke(messages)
            if not isinstance(output, dict):
                raise TypeError(f"答えの形が違います: {output!r}")
            return [
                CourseChoice(item["name"], Relevance(item["relevance"]), item["reason"].strip())
                for item in output["courses"]
            ]
        except (OpenAIRefusalError, ValueError, TypeError, KeyError) as error:
            message = f"{profile.occupation}: LLM の答えを使えません: {error}"
            raise CourseSelectionError(message) from error
