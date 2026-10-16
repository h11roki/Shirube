import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRefusalError
from pydantic import BaseModel, Field, SecretStr

from app.application.ports import OccupationAnalysisError
from app.domain.occupation import SKILL_COUNT, OccupationProfile

INSTRUCTIONS = f"""\
あなたは大学の理工系学部の学生に、なりたい職業に向けた履修を助ける進路アドバイザーです。
入力された職業名について、次の 3 つを答えてください。

- interpretation: その職業名をどの職業と解釈したか。具体的な職業名を 1 行で書く
- assumption: 職業名の解釈が複数に割れるときは、\
電子情報工学科の学生が目指すことの多い解釈を 1 つ選び、\
そう解釈したという前提を 1 文で書く。解釈が割れないときは null
- skills: その職業の仕事で直接使う知識・技能を、\
重要なものから順に {SKILL_COUNT.start}〜{SKILL_COUNT.stop - 1} 個。\
大学の授業で学べる知識・技能の名前として、20 字以内の名詞句で書く

入力が職業名でないときも、最も近い職業として解釈して答えてください。"""


class _Profile(BaseModel):
    interpretation: str = Field(description="解釈した具体的な職業名")
    assumption: str | None = Field(description="解釈が割れたときの前提。割れなければ null")
    skills: list[str] = Field(
        description="仕事で直接使う知識・技能。重要な順",
        min_length=SKILL_COUNT.start,
        max_length=SKILL_COUNT.stop - 1,
    )


class OpenAIOccupationAnalyzer:
    def __init__(
        self, model: str, api_key: SecretStr, http_client: httpx.Client | None = None
    ) -> None:
        chat = ChatOpenAI(model=model, api_key=api_key, http_client=http_client)
        self._client = chat.with_structured_output(_Profile, method="json_schema", strict=True)

    def analyze(self, occupation: str) -> OccupationProfile:
        try:
            output = self._client.invoke([SystemMessage(INSTRUCTIONS), HumanMessage(occupation)])
        except (OpenAIRefusalError, ValueError) as error:
            message = f"{occupation}: LLM の答えを読めません: {error}"
            raise OccupationAnalysisError(message) from error
        if not isinstance(output, _Profile):
            raise OccupationAnalysisError(f"{occupation}: LLM の答えの形が違います: {output!r}")
        return OccupationProfile(
            occupation, output.interpretation, output.assumption, tuple(output.skills)
        )
