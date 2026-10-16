from dataclasses import dataclass

SKILL_COUNT = range(3, 7)


class OccupationProfileError(ValueError):
    pass


@dataclass(frozen=True)
class OccupationProfile:
    occupation: str
    interpretation: str
    assumption: str | None
    skills: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.interpretation.strip():
            raise OccupationProfileError(f"{self.occupation}: 解釈した職業名が空です")
        if self.assumption is not None and not self.assumption.strip():
            raise OccupationProfileError(f"{self.occupation}: 前提が空です")
        if len(self.skills) not in SKILL_COUNT or not all(skill.strip() for skill in self.skills):
            raise OccupationProfileError(
                f"{self.occupation}: スキルは空でないものを {SKILL_COUNT.start}〜"
                f"{SKILL_COUNT.stop - 1} 個にしてください"
            )

    @property
    def query(self) -> str:
        return "\n".join((self.interpretation, *self.skills))
