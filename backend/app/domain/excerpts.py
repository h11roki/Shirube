from dataclasses import dataclass

from app.domain.syllabus import Syllabus

OVERVIEW_LENGTH = 450
OBJECTIVES_LENGTH = 250
SCHEDULE_LENGTH = 350


@dataclass(frozen=True)
class Excerpts:
    overview: str
    objectives: str
    schedule: str


def _cut(text: str, length: int) -> str:
    return " ".join(text.split())[:length]


def excerpts(page: Syllabus) -> Excerpts:
    themes = "、".join(session.theme for session in page.sessions if session.theme.strip())
    return Excerpts(
        _cut(page.overview, OVERVIEW_LENGTH),
        _cut(page.objectives, OBJECTIVES_LENGTH),
        _cut(themes, SCHEDULE_LENGTH),
    )
