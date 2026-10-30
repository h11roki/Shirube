import math
from collections.abc import Sequence
from typing import Self

import httpx
from pydantic import SecretStr

from app.application.ports import Classification, ClassificationError, CourseOdds
from app.domain.excerpts import excerpts
from app.domain.occupation import OccupationProfile
from app.domain.recommendation import CandidateCourse

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
TIMEOUT_SECONDS = 60
SUM_TOLERANCE = 0.01
CORE, FOUNDATION, UNRELATED = "中心", "土台", "関係なし"
CRITERIA = {
    CORE: "授業の中心テーマが、その職業の仕事で直接使う知識・技能そのもの",
    FOUNDATION: "中心の授業を学ぶための基礎(数学、物理、基礎回路、プログラミングの基礎など)、"
    "または授業の一部の回でその職業の知識に触れる",
    UNRELATED: "それ以外",
}
QUESTION = (
    "上の職業を目指す学生にとって、候補の授業「{name}」は次のどれにあたりますか。"
    "科目名だけで決めず、シラバスの抜粋の中身で判断します。中心か土台か迷ったら土台です。"
)


def state(profile: OccupationProfile, candidates: Sequence[CandidateCourse]) -> str:
    lines = [f"職業: {profile.interpretation}"]
    if profile.assumption is not None:
        lines.append(f"前提: {profile.assumption}")
    lines += [f"必要なスキル: {'、'.join(profile.skills)}", "", "候補の授業:"]
    for candidate in candidates:
        material = excerpts(candidate.syllabus)
        lines += [
            "",
            f"## {candidate.name}",
            f"授業の概要と方法: {material.overview}",
            f"到達目標: {material.objectives}",
            f"各回のテーマ: {material.schedule}",
        ]
    return "\n".join(lines)


class JevCourseClassifier:
    def __init__(self, client: httpx.Client, api_key: SecretStr, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    @classmethod
    def connect(cls, api_key: SecretStr, model: str) -> Self:
        return cls(httpx.Client(timeout=TIMEOUT_SECONDS), api_key, model)

    def close(self) -> None:
        self._client.close()

    def classify(
        self, profile: OccupationProfile, candidates: Sequence[CandidateCourse]
    ) -> Classification:
        questions = {
            f"q{index}": {
                "type": "choice",
                "instructions": QUESTION.format(name=candidate.name),
                "criteria": CRITERIA,
            }
            for index, candidate in enumerate(candidates)
        }
        try:
            response = self._client.post(
                ENDPOINT,
                headers={"Authorization": f"Bearer {self._api_key.get_secret_value()}"},
                json={
                    "model": self._model,
                    "state": state(profile, candidates),
                    "questions": questions,
                },
            )
        except httpx.HTTPError as error:
            raise ClassificationError(f"Jev を呼べません: {error}") from error
        if response.status_code != httpx.codes.OK:
            raise ClassificationError(
                f"Jev が {response.status_code} を返しました: {response.text[:300]}"
            )
        try:
            payload = response.json()
            input_tokens = int(payload["usage"]["input_tokens"])
        except (ValueError, KeyError, TypeError) as error:
            raise ClassificationError(f"Jev の答えを読めません: {error!r}") from error
        try:
            odds = []
            for index, candidate in enumerate(candidates):
                probabilities = payload["answers"][f"q{index}"]["probabilities"]
                chances = [float(probabilities[choice]) for choice in (CORE, FOUNDATION, UNRELATED)]
                odds.append(CourseOdds(candidate.name, *chances))
        except (ValueError, KeyError, TypeError) as error:
            raise ClassificationError(f"Jev の答えを読めません: {error!r}", input_tokens) from error
        for each in odds:
            chances = [each.core, each.foundation, each.unrelated]
            if not all(math.isfinite(chance) and 0 <= chance <= 1 for chance in chances) or (
                abs(sum(chances) - 1) > SUM_TOLERANCE
            ):
                raise ClassificationError(
                    f"Jev の確率が 0〜1 に収まらないか、和が 1 になりません: {each.name} {chances}",
                    input_tokens,
                )
        return Classification(tuple(odds), input_tokens)
