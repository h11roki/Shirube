from dataclasses import replace
from uuid import UUID

from app.domain.course import Audience, CourseSection, Term, TimeSlot, Weekday
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan, PlanConditions, PlanResult, PlanStatus
from app.domain.recommendation import (
    CourseChoice,
    Recommendation,
    RecommendedCourse,
    Relevance,
)
from app.domain.roadmap import PlacedCourse, Roadmap, Semester, SemesterPlan
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


SAMPLE_OWNER = UUID("0b7d5a8e-1c1f-4c2a-9a55-3d6f0e1b2c3d")


def sample_plan(plan_id: UUID, owner_id: UUID = SAMPLE_OWNER) -> Plan:
    profile = OccupationProfile("職業", "解釈した職業", "前提の文", ("甲", "乙", "丙"))
    core_a = RecommendedCourse("科目A", "10000", Relevance.CORE, "理由A")
    core_b = RecommendedCourse("科目B", "10001", Relevance.CORE, "理由B")
    foundation_c = RecommendedCourse("科目C", "10002", Relevance.FOUNDATION, "理由C", "科目A")
    foundation_d = RecommendedCourse("科目D", "10003", Relevance.FOUNDATION, "理由D", "科目A")
    recommendation = Recommendation(
        profile,
        (core_a, core_b, foundation_c, foundation_d),
        ("科目A", "科目B", "科目C", "科目D", "科目E", "科目F"),
        (CourseChoice("科目E", Relevance.FOUNDATION, "理由E", "科目F"),),
    )
    year_long = PlacedCourse(
        core_b,
        replace(
            course_section("10001"), name="科目B", term=None, slots=(TimeSlot(Weekday.WED, 3),)
        ),
        True,
    )
    spring = SemesterPlan(
        Semester(3, Term.SPRING),
        (
            PlacedCourse(core_a, replace(course_section("10000"), name="科目A"), True),
            year_long,
            PlacedCourse(
                foundation_c,
                replace(
                    course_section("10002", departments=frozenset({"情"})),
                    name="科目C",
                    class_code="6A",
                    slots=(),
                ),
                False,
            ),
        ),
    )
    roadmap = Roadmap(
        (
            spring,
            SemesterPlan(Semester(3, Term.AUTUMN), (), (year_long,)),
            SemesterPlan(Semester(4, Term.SPRING), ()),
            SemesterPlan(Semester(4, Term.AUTUMN), ()),
        ),
        (foundation_d,),
    )
    return Plan(
        plan_id,
        owner_id,
        sample_conditions(),
        PlanStatus.SUCCEEDED,
        PlanResult(recommendation, roadmap),
    )


def sample_sections() -> tuple[CourseSection, ...]:
    later_only = (Audience(2020, 2026, frozenset({3, 4}), "専門"),)
    return (
        replace(course_section("10000"), name="科目A"),
        replace(
            course_section("10001", slots=(TimeSlot(Weekday.TUE, 1),)),
            name="科目B",
            audiences=later_only,
        ),
        replace(
            course_section("10002", slots=(TimeSlot(Weekday.WED, 1),)),
            name="科目C",
            audiences=later_only,
        ),
        replace(course_section("10003", slots=(TimeSlot(Weekday.THU, 1),)), name="科目D"),
    )


def sample_plan_asking(plan_id: UUID, owner_id: UUID = SAMPLE_OWNER) -> Plan:
    plan = sample_plan(plan_id, owner_id)
    assert plan.result is not None
    return plan.placed_again(
        replace(plan.result.roadmap, offered_earlier=frozenset({"科目A", "科目D"}))
    )


def sample_plan_with_taken(plan_id: UUID, owner_id: UUID = SAMPLE_OWNER) -> Plan:
    plan = sample_plan(plan_id, owner_id)
    assert plan.result is not None
    roadmap = plan.result.roadmap
    return plan.placed_again(
        replace(
            roadmap,
            unplaced=(),
            taken=roadmap.unplaced,
            offered_earlier=frozenset({"科目A", "科目D"}),
        )
    )


def sample_conditions() -> PlanConditions:
    return PlanConditions("職業", "情", 2026, Semester(3, Term.SPRING), (("科目Z", "6B"),), 16)
