from collections import defaultdict
from collections.abc import Set

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session as DbSession

from app.domain.course import Audience, CourseSection, Term, TimeSlot, Weekday
from app.domain.syllabus import CourseName, GradingItem, Session, Syllabus
from app.infrastructure.db.models import (
    AudienceJson,
    CourseSectionRow,
    GradingJson,
    SectionJson,
    SessionJson,
    SlotJson,
    SyllabusCodeRow,
    SyllabusRow,
)


class SqlCourseRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def replace_sections(self, year: int, sections: list[CourseSection]) -> None:
        with DbSession(self._engine) as db, db.begin():
            db.execute(delete(CourseSectionRow).where(CourseSectionRow.year == year))
            db.add_all(CourseSectionRow(year=year, **section_json(section)) for section in sections)

    def replace_syllabi(self, year: int, syllabi: list[Syllabus]) -> None:
        with DbSession(self._engine) as db, db.begin():
            db.execute(delete(SyllabusRow).where(SyllabusRow.year == year))
            db.add_all(_syllabus_row(year, syllabus) for syllabus in syllabi)
            db.flush()
            db.add_all(
                SyllabusCodeRow(
                    year=year,
                    code=name.code,
                    title=name.title,
                    syllabus_code=syllabus.code,
                    position=position,
                )
                for syllabus in syllabi
                for position, name in enumerate(
                    (CourseName(syllabus.code, syllabus.title), *syllabus.aliases)
                )
            )

    def sections(self, year: int) -> list[CourseSection]:
        with DbSession(self._engine) as db:
            rows = db.scalars(
                select(CourseSectionRow)
                .where(CourseSectionRow.year == year)
                .order_by(CourseSectionRow.code)
            )
            return [_section(row) for row in rows]

    def syllabi(self, year: int) -> list[Syllabus]:
        with DbSession(self._engine) as db:
            return _load_syllabi(db, year)

    def syllabi_of(self, year: int, primary_codes: Set[str]) -> dict[str, Syllabus]:
        with DbSession(self._engine) as db:
            return {page.code: page for page in _load_syllabi(db, year, primary_codes)}

    def syllabus_codes(self, year: int) -> dict[str, str]:
        with DbSession(self._engine) as db:
            rows = db.execute(
                select(SyllabusCodeRow.code, SyllabusCodeRow.syllabus_code).where(
                    SyllabusCodeRow.year == year
                )
            )
            return {code: syllabus_code for code, syllabus_code in rows}

    def syllabus_urls(self, year: int, primary_codes: Set[str]) -> dict[str, str]:
        with DbSession(self._engine) as db:
            rows = db.execute(
                select(SyllabusRow.code, SyllabusRow.url).where(
                    SyllabusRow.year == year,
                    SyllabusRow.code.in_(primary_codes),
                    SyllabusRow.url.is_not(None),
                )
            )
            return {code: url for code, url in rows if url is not None}


def _load_syllabi(
    db: DbSession, year: int, primary_codes: Set[str] | None = None
) -> list[Syllabus]:
    names = select(SyllabusCodeRow).where(
        SyllabusCodeRow.year == year, SyllabusCodeRow.position > 0
    )
    rows = select(SyllabusRow).where(SyllabusRow.year == year)
    if primary_codes is not None:
        names = names.where(SyllabusCodeRow.syllabus_code.in_(primary_codes))
        rows = rows.where(SyllabusRow.code.in_(primary_codes))
    aliases: dict[str, list[CourseName]] = defaultdict(list)
    for name in db.scalars(names.order_by(SyllabusCodeRow.syllabus_code, SyllabusCodeRow.position)):
        aliases[name.syllabus_code].append(CourseName(name.code, name.title))
    return [
        _syllabus(row, tuple(aliases[row.code]))
        for row in db.scalars(rows.order_by(SyllabusRow.code))
    ]


def section_json(section: CourseSection) -> SectionJson:
    return SectionJson(
        code=section.code,
        name=section.name,
        class_code=section.class_code,
        term=section.term.value if section.term is not None else None,
        slots=[SlotJson(weekday=slot.weekday.value, period=slot.period) for slot in section.slots],
        departments=sorted(section.departments) if section.departments is not None else None,
        audiences=[
            AudienceJson(
                entry_year_from=audience.entry_year_from,
                entry_year_to=audience.entry_year_to,
                eligible_grades=sorted(audience.eligible_grades),
                category=audience.category,
            )
            for audience in section.audiences
        ],
        credits=section.credits,
        instructors=list(section.instructors),
        room=section.room,
        registration=section.registration,
        note=section.note,
    )


def section_from_json(data: SectionJson) -> CourseSection:
    return CourseSection(
        code=data["code"],
        name=data["name"],
        class_code=data["class_code"],
        term=Term(data["term"]) if data["term"] is not None else None,
        slots=tuple(TimeSlot(Weekday(slot["weekday"]), slot["period"]) for slot in data["slots"]),
        departments=frozenset(data["departments"]) if data["departments"] is not None else None,
        audiences=tuple(
            Audience(
                audience["entry_year_from"],
                audience["entry_year_to"],
                frozenset(audience["eligible_grades"]),
                audience["category"],
            )
            for audience in data["audiences"]
        ),
        credits=data["credits"],
        instructors=tuple(data["instructors"]),
        room=data["room"],
        registration=data["registration"],
        note=data["note"],
    )


def _section(row: CourseSectionRow) -> CourseSection:
    return section_from_json(
        SectionJson(
            code=row.code,
            name=row.name,
            class_code=row.class_code,
            term=row.term,
            slots=row.slots,
            departments=row.departments,
            audiences=row.audiences,
            credits=row.credits,
            instructors=row.instructors,
            room=row.room,
            registration=row.registration,
            note=row.note,
        )
    )


def _syllabus_row(year: int, syllabus: Syllabus) -> SyllabusRow:
    return SyllabusRow(
        year=year,
        code=syllabus.code,
        title=syllabus.title,
        term_label=syllabus.term_label,
        slot_label=syllabus.slot_label,
        faculties=list(syllabus.faculties),
        instructors=list(syllabus.instructors),
        credits=syllabus.credits,
        campus=syllabus.campus,
        language=syllabus.language,
        overview=syllabus.overview,
        objectives=syllabus.objectives,
        preparation=syllabus.preparation,
        schedule_note=syllabus.schedule_note,
        sessions=[
            SessionJson(label=session.label, theme=session.theme, keywords=session.keywords)
            for session in syllabus.sessions
        ],
        class_format=syllabus.class_format,
        self_study=syllabus.self_study,
        grading=[
            GradingJson(kind=item.kind, percentage=item.percentage, criteria=item.criteria)
            for item in syllabus.grading
        ],
        grading_note=syllabus.grading_note,
        advice=syllabus.advice,
        remarks=syllabus.remarks,
        url=syllabus.url,
    )


def _syllabus(row: SyllabusRow, aliases: tuple[CourseName, ...]) -> Syllabus:
    return Syllabus(
        code=row.code,
        title=row.title,
        aliases=aliases,
        year=row.year,
        term_label=row.term_label,
        slot_label=row.slot_label,
        faculties=tuple(row.faculties),
        instructors=tuple(row.instructors),
        credits=row.credits,
        campus=row.campus,
        language=row.language,
        overview=row.overview,
        objectives=row.objectives,
        preparation=row.preparation,
        schedule_note=row.schedule_note,
        sessions=tuple(Session(**session) for session in row.sessions),
        class_format=row.class_format,
        self_study=row.self_study,
        grading=tuple(GradingItem(**item) for item in row.grading),
        grading_note=row.grading_note,
        advice=row.advice,
        remarks=row.remarks,
        url=row.url,
    )
