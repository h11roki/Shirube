import json
from typing import Literal, Self

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRefusalError
from openai import (
    BadRequestError,
    ContentFilterFinishReasonError,
    LengthFinishReasonError,
    OpenAIError,
)
from pydantic import BaseModel, Field, SecretStr

from app.application.ports import ReasonJudgeError, ReasonJudgeUnavailableError
from app.application.reason_judging import (
    KIND_LABELS,
    WHY_LENGTH,
    ReasonCase,
    ReasonGrade,
    ReasonVote,
)
from app.domain.recommendation import Relevance

NO_EVIDENCE = "根拠なし"

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

判定の手順

柱の理由

1. 理由の文から、職業や仕事、職業の分野に向けて書いた部分を quote にそのまま写す。\
「設計の土台となる」「IT実装の入口になる」「実務に直結する」も、職業の分野に向けた部分なので写す。\
授業で扱う技術や活動を並べた部分(「回路を設計し、シミュレーションで確かめる」など)は、\
授業の中身であって職業の仕事の中身ではないので写さない。写すものが無ければ quote は空で、absent
2. quote が、職業の人のする作業、作るもの、扱う対象を名指しし、\
授業で学ぶことがそこでどう使われるかを言っていれば specific。\
職業や分野の名前に「実務に直結」「設計の土台」「〜の基礎」「〜に必要」を付けただけなら vague

礎の理由

1. 理由の文から、つながる柱の科目名、柱で扱う内容、柱の分野のどれかに触れた部分を\
quote にそのまま写す。写すものが無ければ quote は空で、absent
2. この授業で学ぶ内容が書いてあり、それを柱(科目名か内容)で使うことが読み取れれば specific。\
柱のどの単元で使うかまで書いていなくてよい。\
この授業で学ぶ内容が無いか、柱や分野の名前に「基礎になる」「理解に役立つ」を付けただけなら vague

実際の理由の例(職業 / 授業。礎はつながる柱も)

- 柱 specific(FPGA エンジニア / ハードウェア記述言語): Verilog HDLで組み合わせ回路・順序回路を\
設計し、シミュレーションで動作確認する。FPGA実装に直結するHDL記述力が身につく。\
(FPGA に実装する仕事に HDL の記述力を使うと分かる)
- 柱 vague(電子回路設計エンジニア / 電子回路Ⅰ): MOSトランジスタやPN接合の基礎、小信号等価回路、\
各種接地回路を学び、設計の土台となる動作理解が得られるため。(「設計の土台」だけで、\
仕事のどこに使うかが無い)
- 柱 vague(IT エンジニア / データエンジニアリング基礎): ビッグデータの収集・整形・蓄積、\
データベース抽出、可視化まで扱い、ITエンジニアの実務に直結する。(職業の名前に「実務に直結」を\
付けただけ)
- 柱 absent(放送・映像機器の技術者 / 通信理論): データを双方向でやりとりする原理を、\
同期・誤り制御・復調など具体技術と計算パラメータで理解できるため。(授業の技術を並べるだけで、\
職業に触れていない)
- 柱 absent(電子回路設計エンジニア / 電子回路Ⅱ): MOSFET中心に増幅回路、差動増幅、カレントミラー、\
オペアンプ演算回路を特性解析と設計として扱うため。(「設計」は授業で扱うことで、\
職業の仕事に結び付けていない)
- 礎 specific(FPGA エンジニア / コンピュータアーキテクチャⅡ → 組み込みシステム): \
組み込みシステムで必要なプロセッサやメモリの方式(記憶階層、キャッシュ、入出力制御)を理解する\
前提になる。(柱の名前と、柱で使う内容が分かる)
- 礎 specific(組込みソフトウェアエンジニア / 情報処理 → 応用Cプログラミング): \
情報処理でCの文法を学び、応用Cの「Cのより高度な使用法」やデータ構造の実現へつながるため。\
(C の文法が、柱の高度な使い方とデータ構造の前提と分かる)
- 礎 vague(IT営業 / オペレーティングシステム → 情報科学Ⅱ): OSの概念や機能、プロセス管理、\
同期と通信、実記憶/仮想記憶管理、入出力制御を理解し、情報技術の本質理解の前提になる。\
(柱の分野の「情報技術」には触れるが、柱の名前も、柱のどの内容かも無い)

次のことは判定に入れません。

- 理由の中身が事実か(授業で本当に扱うか)
- 文の長さ、言い回しの上手さ、誤字
- その授業を薦めたこと自体の良し悪し

まず quote を写し、次に根拠を {WHY_LENGTH} 字以内で書き、そのあと段を決めます。根拠には、\
職業の仕事の中身(柱)か柱の内容(礎)として何を挙げているか、または何が無いかを書きます。"""


class _Verdict(BaseModel):
    quote: str = Field(
        description="柱なら職業や仕事について書いた部分、礎なら柱に触れた部分を、理由の文から"
        "そのまま写す。無ければ空"
    )
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


SAMPLE_CASES = (
    ReasonCase("職業名", "職業", "前提", Relevance.CORE, "授業", None, "理由"),
    ReasonCase("職業名", "職業", None, Relevance.FOUNDATION, "授業", "柱の授業", "理由"),
)
JUDGE_PROMPT = "\n".join(
    [
        INSTRUCTIONS,
        json.dumps(_Verdict.model_json_schema(), ensure_ascii=False, sort_keys=True),
        *(_request(case) for case in SAMPLE_CASES),
    ]
)


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
            why = output.why.strip()[:WHY_LENGTH] or NO_EVIDENCE
            return ReasonVote(ReasonGrade(output.grade), why)
        except (
            OpenAIRefusalError,
            ContentFilterFinishReasonError,
            LengthFinishReasonError,
            BadRequestError,
            ValueError,
            TypeError,
        ) as error:
            message = f"{case.occupation} の {case.course}: LLM の答えを使えません: {error}"
            raise ReasonJudgeError(message) from error
        except OpenAIError as error:
            message = (
                f"{case.occupation} の {case.course}: OpenAI の API 呼び出しに失敗しました: {error}"
            )
            raise ReasonJudgeUnavailableError(message) from error
