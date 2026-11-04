from typing import Literal, Self

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRefusalError
from openai import ContentFilterFinishReasonError, LengthFinishReasonError, OpenAIError
from pydantic import BaseModel, Field, SecretStr

from app.application.ports import ReasonJudgeError
from app.application.reason_judging import WHY_LENGTH, ReasonCase, ReasonGrade, ReasonVote
from app.domain.recommendation import Relevance

INSTRUCTIONS = f"""\
あなたは、大学の授業を薦めるアプリが書いた「取るべき理由」の文を判定する判定者です。

アプリは、なりたい職業を入れた学生に、授業を「柱」と「礎」に分けて薦め、授業ごとに理由の文を付けます。

- 柱: その職業の仕事で直接使う知識や技能を学ぶ授業
- 礎: 柱の授業を学ぶ前提になる授業。どの柱の前提かが「つながる柱」にある

理由の文が、次の決まりのどの段に当たるかを判定します。柱と礎で、見ることが違います。

柱の理由は「職業とのつながり」を見ます。

- specific(具体的): 職業の仕事の中身(する作業、作るもの、扱う対象、使う技能)を 1 つ以上挙げ、\
授業で学ぶことがそこにどう使われるかが分かる
- vague(ぼんやり): 職業や分野、「実務」「業務」には触れるが、\
「役立つ」「直結する」「必須」「基礎になる」だけで、仕事のどこにどう使うかが分からない
- absent(無い): 授業で学ぶことの紹介だけで、職業にも仕事にも触れていない。\
授業で身につく技能を挙げるだけで、職業の仕事に結び付けていないものも absent にする

礎の理由は「柱の前提」を見ます。

- specific(具体的): つながる柱の授業(科目名か、その授業で扱う内容)を挙げ、\
この授業のどの内容が、柱のどの内容の前提になるかが分かる
- vague(ぼんやり): 柱の授業や分野には触れるが、「基礎になる」「理解に役立つ」だけで、\
柱のどの内容の前提かが分からない
- absent(無い): 柱の授業にも、その内容にも触れていない。職業に触れるだけのものも absent にする

例(作った例です。職業は「鉄道の運行管理システムのエンジニア」、柱は「待ち行列理論」、\
礎は「確率論入門」で、礎は「待ち行列理論」の前提とします)

- 柱 specific: 到着と待ちの確率モデルを学び、列車の遅れが駅や路線へ広がる様子を見積もって\
運行計画を検討するのに使える
- 柱 vague: 待ち行列のモデルを学び、運行管理システムの開発の実務に直結する
- 柱 absent: 到着の分布と待ち時間の求め方を、演習で計算して身につける
- 礎 specific: 確率変数と指数分布を学び、待ち行列理論で到着の間隔と待ち時間の分布を扱う前提になる
- 礎 vague: 確率の基礎を学び、待ち行列理論の理解に役立つ
- 礎 absent: 確率の考え方を身につけ、運行管理の仕事に役立つ

次のことは判定に入れません。

- 理由の中身が事実か(授業で本当に扱うか)
- 文の長さ、言い回しの上手さ、誤字
- その授業を薦めたこと自体の良し悪し

まず根拠を {WHY_LENGTH} 字以内で書き、そのあと段を決めます。根拠には、職業の仕事の中身(柱)か\
柱の内容(礎)として何を挙げているか、または何が無いかを書きます。"""

KIND_LABELS = {Relevance.CORE: "柱", Relevance.FOUNDATION: "礎"}


class _Verdict(BaseModel):
    why: str = Field(description=f"段を決めた根拠。{WHY_LENGTH} 字以内")
    grade: Literal["specific", "vague", "absent"] = Field(description="理由の文の段")


def _request(case: ReasonCase) -> str:
    lines = [f"職業: {case.interpretation}"]
    if case.assumption is not None:
        lines.append(f"職業の解釈の前提: {case.assumption}")
    lines += [f"種類: {KIND_LABELS[case.relevance]}", f"授業: {case.course}"]
    if case.pillar is not None:
        lines.append(f"つながる柱: {case.pillar}")
    lines.append(f"理由: {case.reason}")
    return "\n".join(lines)


class OpenAIReasonJudge:
    def __init__(self, chat: ChatOpenAI) -> None:
        self._client = chat.with_structured_output(_Verdict, method="json_schema", strict=True)

    @classmethod
    def connect(cls, model: str, api_key: SecretStr, timeout: float, retries: int) -> Self:
        return cls(ChatOpenAI(model=model, api_key=api_key, timeout=timeout, max_retries=retries))

    def judge(self, case: ReasonCase) -> ReasonVote:
        messages = [SystemMessage(INSTRUCTIONS), HumanMessage(_request(case))]
        try:
            output = self._client.invoke(messages)
            if not isinstance(output, _Verdict):
                raise TypeError(f"答えの形が違います: {output!r}")
            return ReasonVote(ReasonGrade(output.grade), output.why.strip()[:WHY_LENGTH])
        except (
            OpenAIRefusalError,
            ContentFilterFinishReasonError,
            LengthFinishReasonError,
            ValueError,
            TypeError,
        ) as error:
            message = f"{case.occupation} の {case.course}: LLM の答えを使えません: {error}"
            raise ReasonJudgeError(message) from error
        except OpenAIError as error:
            message = (
                f"{case.occupation} の {case.course}: OpenAI の API 呼び出しに失敗しました: {error}"
            )
            raise ReasonJudgeError(message) from error
