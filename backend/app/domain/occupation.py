import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

SKILL_COUNT = range(3, 7)
READABLE = re.compile(
    "[\u0020-\u007e\u00a0-\u00ac\u00ae-\u00ff\u0300-\u03ff\u2010-\u2027\u2030-\u205e"
    "\u2070-\u23ff\u2460-\u24ff\u25a0-\u27bf\u3000-\u30ff\u3200-\u4dbf\u4e00-\u9fff"
    "\uf900-\ufaff\uff00-\uffef\U00020000-\U0003134f]*"
)


class OccupationProfileError(ValueError):
    pass


def is_single_line(text: str) -> bool:
    return bool(text.strip()) and text.splitlines() == [text]


def is_readable(text: str) -> bool:
    return READABLE.fullmatch(text) is not None


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
        if not is_single_line(self.interpretation):
            raise OccupationProfileError(
                f"{self.occupation}: 解釈した職業名は空でない 1 行にしてください"
            )
        if self.assumption is not None and not self.assumption.strip():
            raise OccupationProfileError(f"{self.occupation}: 前提が空です")
        if len(self.skills) not in SKILL_COUNT:
            raise OccupationProfileError(
                f"{self.occupation}: スキルは "
                f"{SKILL_COUNT.start}〜{SKILL_COUNT.stop - 1} 個にしてください"
            )
        if not all(is_single_line(skill) for skill in self.skills):
            raise OccupationProfileError(f"{self.occupation}: スキルは空でない 1 行にしてください")
        if len({skill.strip() for skill in self.skills}) != len(self.skills):
            raise OccupationProfileError(f"{self.occupation}: スキルが重複しています")

    @classmethod
    def read(
        cls,
        occupation: str,
        interpretation: str,
        assumption: str | None,
        skills: tuple[str, ...],
    ) -> Self:
        return cls(occupation, interpretation if assumption else occupation, assumption, skills)

    @property
    def unreadable_parts(self) -> tuple[str, ...]:
        typed = set(self.occupation)
        written = (
            self.interpretation,
            *((self.assumption,) if self.assumption else ()),
            *self.skills,
        )
        return tuple(
            text
            for text in written
            if not is_readable("".join(letter for letter in text if letter not in typed))
        )

    @property
    def query(self) -> str:
        return search_query(self.interpretation, self.skills)
