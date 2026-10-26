import logging
from typing import Self

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRefusalError
from openai import ContentFilterFinishReasonError, LengthFinishReasonError, OpenAIError
from pydantic import BaseModel, Field, SecretStr

from app.application.ports import OccupationAnalysisError
from app.domain.occupation import SKILL_COUNT, OccupationProfile

READ_ATTEMPTS = 2

logger = logging.getLogger(__name__)

DEPARTMENT_FIELDS = """\
- 電気回路、電子回路、電磁気学
- 半導体工学、集積デバイス
- 高周波工学、通信理論、情報理論
- 信号処理、メディア情報処理、映像メディア
- 制御工学、組み込みシステム
- 論理回路、コンピュータアーキテクチャ、ハードウェア記述言語、システム設計の CAD
- プログラミング(C 言語)、データ構造とアルゴリズム、コンパイラ
- オペレーティングシステム、並列処理、コンピュータネットワーク
- ソフトウェア工学
- データサイエンス、データエンジニアリング、AI・機械学習、深層学習
- 数学(微分積分、線形代数、確率統計、フーリエ解析、複素関数、数理計画法)
- 物理(力学、熱力学、振動と波動)、化学、材料
- エネルギーの活用と状態推定(EV、蓄電池)
- 情報社会と倫理、技術者倫理
- 教職(現代の教育、情報と職業、職業指導、教育とコンピュータ)
- 経営と起業(現代の経営、企業と社会、アントレプレナーシップ)
- 課題解決の実践とキャリア(コーオプ演習、社会と学ぶ課題解決)
- 計算言語学(英語の教養科目)"""

INSTRUCTIONS = f"""\
あなたは大学の理工系学部の学生に、なりたい職業に向けた履修を助ける進路アドバイザーです。
学生は電子情報工学科に在籍しています。学科で学べる分野は次のとおりです。

{DEPARTMENT_FIELDS}

入力された職業名について、次の 4 つを順に答えてください。

- department_field: 職業名で仕事を決めている分野が、上の学科の分野のどれかに当たるなら、\
当たる分野の名前を 1 つ書く。どれにも当たらなければ null
- interpretation: その職業名をどの職業と解釈したか。\
解釈した職業名を、職業の名前として短く 1 行で書く。\
department_field があるときと、広く読むか迷うときは、\
入力された職業名を言い換えずにそのまま書く。\
department_field が null で、職業名が、上の学科の分野に無い応用分野や、\
授業で扱わない道具や製品で決まる細かい職種(Webエンジニア、フロントエンドエンジニア、スマホアプリ開発者、クラウドエンジニアなど)\
のときだけ、学科の授業で備えられる広い職業として解釈する。\
例えば「Webエンジニア」は「ITエンジニア」と読む。\
広く読むときも、仕事の役割(開発、研究、教育、営業、経営、企画など)は解釈に残す。\
上の分野の名前を、そのまま職業名にしない
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
C 言語や Python のように授業で使うプログラミング言語は、名前で書いてよい。\
職業名に含まれる分野と、その職業の役割の中心になる知識のうち、上の学科の分野にあるものは、\
スキルに入れる。役割に関わらない分野を、数合わせに入れない

入力が職業名でないときも、最も近い職業として解釈し、\
そう解釈したという前提を assumption に 1 文で書いてください。"""


class _Profile(BaseModel):
    department_field: str | None = Field(description="当たる学科の分野。無ければ null")
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
        unreadable: list[str] = []
        for attempt in range(1, READ_ATTEMPTS + 1):
            profile = self._profile(occupation)
            parts = profile.unreadable_parts
            if not parts:
                return profile
            unreadable.extend(parts)
            if attempt < READ_ATTEMPTS:
                logger.warning(
                    "%s: LLM の答えに使えない文字が混ざっていたので聞き直します: %s",
                    occupation,
                    parts,
                )
        listed = "、".join(dict.fromkeys(unreadable))
        raise OccupationAnalysisError(
            f"{occupation}: LLM の答えに使えない文字が混ざっています: {listed}"
        )

    def _profile(self, occupation: str) -> OccupationProfile:
        try:
            output = self._client.invoke([SystemMessage(INSTRUCTIONS), HumanMessage(occupation)])
            if not isinstance(output, _Profile):
                raise TypeError(f"答えの形が違います: {output!r}")
            assumption = output.assumption.strip() if output.assumption else None
            return OccupationProfile.read(
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
