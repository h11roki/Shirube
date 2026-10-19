from typing import Self

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRefusalError
from openai import ContentFilterFinishReasonError, LengthFinishReasonError, OpenAIError
from pydantic import BaseModel, Field, SecretStr

from app.application.ports import OccupationAnalysisError
from app.domain.occupation import SKILL_COUNT, OccupationProfile

INSTRUCTIONS = f"""\
あなたは大学の理工系学部の学生に、なりたい職業に向けた履修を助ける進路アドバイザーです。
入力された職業名について、次の 3 つを答えてください。

- interpretation: その職業名をどの職業と解釈したか。解釈した職業名を短く 1 行で書く。\
電子情報工学科の授業がそのまま備える職業(組込み、半導体、通信、制御、データ分析など)は、\
そのまま解釈する。職業名が、学科の授業に無い応用分野や、授業で扱わない道具や製品で決まる\
細かい職種(Webエンジニア、フロントエンドエンジニア、スマホアプリ開発者、クラウドエンジニアなど)\
のときだけ、学科の授業で備えられる広い職業として解釈する。\
例えば「Webエンジニア」は「ITエンジニア」と読む
- assumption: 職業名の解釈が複数に割れるときは、\
電子情報工学科の学生が目指すことの多い解釈を 1 つ選び、\
そう解釈したという前提を 1 文で書く。細かい職種を広い職業として読んだときも、\
そう読んだことと理由を前提に 1 文で書く\
(例: Webエンジニアを、Web を含むソフトウェア開発全般の IT エンジニアとして読んだ)。\
どちらでもないときは null
- skills: その職業の仕事で直接使う知識・技能を、\
重要なものから順に {SKILL_COUNT.start}〜{SKILL_COUNT.stop - 1} 個。重複させない。\
大学の授業で学べる知識・技能の名前として、20 字以内の名詞句で書く。\
特定のフレームワーク、製品、サービスの名前ではなく、授業で学ぶ分野の名前で書く\
(例: React ではなく Web の仕組みとプログラミング)。\
C 言語や Python のように授業で使うプログラミング言語は、名前で書いてよい

入力が職業名でないときも、最も近い職業として解釈して答えてください。"""


class _Profile(BaseModel):
    interpretation: str = Field(description="解釈した職業名")
    assumption: str | None = Field(description="前提の 1 文。書かないときは null")
    skills: list[str] = Field(
        description="仕事で直接使う知識・技能。重要な順",
        min_length=SKILL_COUNT.start,
        max_length=SKILL_COUNT.stop - 1,
    )


class OpenAIOccupationAnalyzer:
    def __init__(self, chat: ChatOpenAI) -> None:
        self._client = chat.with_structured_output(_Profile, method="json_schema", strict=True)

    @classmethod
    def connect(cls, model: str, api_key: SecretStr, timeout: float, retries: int) -> Self:
        return cls(ChatOpenAI(model=model, api_key=api_key, timeout=timeout, max_retries=retries))

    def analyze(self, occupation: str) -> OccupationProfile:
        try:
            output = self._client.invoke([SystemMessage(INSTRUCTIONS), HumanMessage(occupation)])
            if not isinstance(output, _Profile):
                raise TypeError(f"答えの形が違います: {output!r}")
            assumption = output.assumption.strip() if output.assumption else None
            return OccupationProfile(
                occupation,
                output.interpretation.strip(),
                assumption or None,
                tuple(skill.strip() for skill in output.skills),
            )
        except (
            OpenAIRefusalError,
            ContentFilterFinishReasonError,
            LengthFinishReasonError,
            ValueError,
            TypeError,
        ) as error:
            message = f"{occupation}: LLM の答えを使えません: {error}"
            raise OccupationAnalysisError(message) from error
        except OpenAIError as error:
            message = f"{occupation}: OpenAI の API 呼び出しに失敗しました: {error}"
            raise OccupationAnalysisError(message) from error
