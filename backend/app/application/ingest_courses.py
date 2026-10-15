from collections.abc import Sequence
from dataclasses import dataclass

from app.application.ports import CourseRepository, SyllabusSource, TimetableSource
from app.domain.course import CourseSection


class IngestError(ValueError):
    pass


@dataclass(frozen=True)
class SyllabusReport:
    pages: int
    codes_without_syllabus: tuple[str, ...]


class IngestTimetable:
    def __init__(self, sources: Sequence[TimetableSource], repository: CourseRepository) -> None:
        self._sources = sources
        self._repository = repository

    def run(self, year: int) -> int:
        sections: dict[str, CourseSection] = {}
        for source in self._sources:
            for section in source.sections():
                if sections.setdefault(section.code, section) != section:
                    raise IngestError(f"{section.code} が時間割表に内容を変えて 2 回現れます")
        if not sections:
            raise IngestError("時間割表から科目を 1 件も読めません")
        newest = max(
            (audience.entry_year_to for s in sections.values() for audience in s.audiences),
            default=None,
        )
        if newest != year:
            raise IngestError(f"時間割表の最も新しい入学年度 {newest} が {year} と違います")
        self._repository.replace_sections(year, list(sections.values()))
        return len(sections)


class IngestSyllabi:
    def __init__(self, source: SyllabusSource, repository: CourseRepository) -> None:
        self._source = source
        self._repository = repository

    def run(self, year: int) -> SyllabusReport:
        syllabi = self._source.syllabi()
        if not syllabi:
            raise IngestError("保存済みのシラバスがありません")
        page_of: dict[str, str] = {}
        for syllabus in syllabi:
            if syllabus.year != year:
                raise IngestError(
                    f"{syllabus.code}: シラバスの年度 {syllabus.year} が {year} と違います"
                )
            for code in (syllabus.code, *(alias.code for alias in syllabus.aliases)):
                if page_of.setdefault(code, syllabus.code) != syllabus.code:
                    raise IngestError(
                        f"{code} が 2 つのページ {page_of[code]} {syllabus.code} に現れます"
                    )
        self._repository.replace_syllabi(year, syllabi)
        missing = tuple(
            section.code
            for section in self._repository.sections(year)
            if section.code not in page_of
        )
        return SyllabusReport(len(syllabi), missing)
