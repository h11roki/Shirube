import logging
from dataclasses import dataclass

from app.application.ports import (
    CourseRepository,
    ListingConflictError,
    SyllabusSource,
    TimetableSource,
)
from app.domain.syllabus import Syllabus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestReport:
    sections: int
    syllabi: int
    codes_without_syllabus: tuple[str, ...]


class IngestCourses:
    def __init__(
        self, timetable: TimetableSource, syllabi: SyllabusSource, repository: CourseRepository
    ) -> None:
        self._timetable = timetable
        self._syllabi = syllabi
        self._repository = repository

    def run(self, year: int) -> IngestReport:
        sections = self._timetable.sections()
        syllabi: dict[str, Syllabus] = {}
        missing: list[str] = []
        for section in sections:
            try:
                syllabus = self._syllabi.syllabus(section.code)
            except ListingConflictError as error:
                logger.warning("%s", error)
                syllabus = None
            if syllabus is None:
                missing.append(section.code)
                continue
            if syllabus.year != year:
                raise ValueError(f"{section.code}: シラバスの年度 {syllabus.year} が {year} と違う")
            syllabi.setdefault(syllabus.code, syllabus)
        self._repository.replace(year, sections, list(syllabi.values()))
        return IngestReport(len(sections), len(syllabi), tuple(missing))
