from collections.abc import Sequence
from dataclasses import dataclass

SKILL_COUNT = range(3, 7)


class OccupationProfileError(ValueError):
    pass


def search_query(occupation: str, skills: Sequence[str]) -> str:
    return "\n".join((occupation, *skills))


@dataclass(frozen=True)
class OccupationProfile:
    occupation: str
    interpretation: str
    assumption: str | None
    skills: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.occupation.strip():
            raise OccupationProfileError("職業名が空です")
        if not self.interpretation.strip() or "\n" in self.interpretation:
            raise OccupationProfileError(f"{self.occupation}: 解釈した職業名は 1 行にしてください")
        if self.assumption is not None and not self.assumption.strip():
            raise OccupationProfileError(f"{self.occupation}: 前提が空です")
        if len(self.skills) not in SKILL_COUNT or not all(
            skill.strip() and "\n" not in skill for skill in self.skills
        ):
            raise OccupationProfileError(
                f"{self.occupation}: スキルは 1 行のものを {SKILL_COUNT.start}〜"
                f"{SKILL_COUNT.stop - 1} 個にしてください"
            )

    @property
    def query(self) -> str:
        return search_query(self.interpretation, self.skills)
