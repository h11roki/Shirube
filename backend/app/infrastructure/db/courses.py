from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session as DbSession

from app.domain.course import Audience, CourseSection, Term, TimeSlot, Weekday
from app.domain.syllabus import CourseName, GradingItem, Session, Syllabus
from app.infrastructure.db.models import (
    AudienceJson,
    CourseSectionRow,
    GradingJson,
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
            db.add_all(_section_row(year, section) for section in sections)

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

    def syllabus(self, year: int, code: str) -> Syllabus | None:
        with DbSession(self._engine) as db:
            primary_code = db.scalar(
                select(SyllabusCodeRow.syllabus_code).where(
                    SyllabusCodeRow.year == year, SyllabusCodeRow.code == code
                )
            )
            if primary_code is None:
                return None
            names = db.scalars(
                select(SyllabusCodeRow)
                .where(SyllabusCodeRow.year == year, SyllabusCodeRow.syllabus_code == primary_code)
                .order_by(SyllabusCodeRow.position)
            )
            aliases = tuple(CourseName(name.code, name.title) for name in names if name.position)
            return _syllabus(db.get_one(SyllabusRow, (year, primary_code)), aliases)


def _section_row(year: int, section: CourseSection) -> CourseSectionRow:
    return CourseSectionRow(
        year=year,
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


def _section(row: CourseSectionRow) -> CourseSection:
    return CourseSection(
        code=row.code,
        name=row.name,
        class_code=row.class_code,
        term=Term(row.term) if row.term is not None else None,
        slots=tuple(TimeSlot(Weekday(slot["weekday"]), slot["period"]) for slot in row.slots),
        departments=frozenset(row.departments) if row.departments is not None else None,
        audiences=tuple(
            Audience(
                audience["entry_year_from"],
                audience["entry_year_to"],
                frozenset(audience["eligible_grades"]),
                audience["category"],
            )
            for audience in row.audiences
        ),
        credits=row.credits,
        instructors=tuple(row.instructors),
        room=row.room,
        registration=row.registration,
        note=row.note,
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
    )
