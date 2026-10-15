from app.domain.course import Audience, CourseSection, Term, TimeSlot, Weekday
from app.domain.syllabus import CourseName, GradingItem, Session, Syllabus


def course_section(
    code: str,
    term: Term | None = Term.SPRING,
    slots: tuple[TimeSlot, ...] = (TimeSlot(Weekday.MON, 1), TimeSlot(Weekday.MON, 2)),
    departments: frozenset[str] | None = frozenset({"電", "情"}),
) -> CourseSection:
    return CourseSection(
        code=code,
        name=f"科目{code}",
        class_code="6T",
        term=term,
        slots=slots,
        departments=departments,
        audiences=(
            Audience(2020, 2026, frozenset({1, 2, 3, 4}), "専門"),
            Audience(2016, 2019, frozenset({2}), "基礎専"),
        ),
        credits=2,
        instructors=("教員 甲", "教員 乙"),
        room="F101",
        registration="本",
        note=None,
    )


def syllabus(code: str, aliases: tuple[CourseName, ...] = (), year: int = 2026) -> Syllabus:
    return Syllabus(
        code=code,
        title=f"科目{code}(6T)",
        aliases=aliases,
        year=year,
        term_label="春セメスター",
        slot_label="月1",
        faculties=("理工学部",),
        instructors=("教員 甲",),
        credits=2,
        campus="BKC",
        language="日本語",
        overview="概要\n\n段落",
        objectives="目標",
        preparation="なし",
        schedule_note="注記",
        sessions=(Session("1", "導入", "語"), Session("2-3", "展開", "語\n語")),
        class_format="対面",
        self_study="予習",
        grading=(GradingItem("定期試験", "100", "基準"),),
        grading_note="",
        advice="",
        remarks="",
    )
