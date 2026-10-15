import hashlib
from dataclasses import dataclass
from enum import Enum
from functools import cached_property

from app.domain.syllabus import Syllabus


class ChunkSection(Enum):
    OVERVIEW = "overview"
    OBJECTIVES = "objectives"
    SCHEDULE = "schedule"


SECTION_HEADINGS = {
    ChunkSection.OVERVIEW: "授業の概要と方法",
    ChunkSection.OBJECTIVES: "受講生の到達目標",
    ChunkSection.SCHEDULE: "授業スケジュール",
}


@dataclass(frozen=True)
class SyllabusChunk:
    syllabus_code: str
    section: ChunkSection
    text: str

    @cached_property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def chunks_of(syllabus: Syllabus) -> list[SyllabusChunk]:
    schedule = "\n".join(
        line
        for session in syllabus.sessions
        for line in (session.theme, session.keywords)
        if line.strip()
    )
    bodies = {
        ChunkSection.OVERVIEW: syllabus.overview,
        ChunkSection.OBJECTIVES: syllabus.objectives,
        ChunkSection.SCHEDULE: schedule,
    }
    return [
        SyllabusChunk(
            syllabus.code, section, f"{syllabus.title}\n{SECTION_HEADINGS[section]}\n{body.strip()}"
        )
        for section, body in bodies.items()
        if body.strip()
    ]
