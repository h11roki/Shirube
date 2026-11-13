from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.application.syllabus_links import PlanLinks
from app.domain.course import ALL_GRADES, Term, Weekday
from app.domain.occupation import OccupationProfile, is_single_line
from app.domain.plan import Plan, PlanResult, PlanStage, PlanStatus
from app.domain.roadmap import FixedCourse, PlacedCourse, PlannedCourse

MAX_CHOSEN_CLASSES = 50
MAX_FIXED_COURSES = 30
MAX_NAME_LENGTH = 100
FIXED = "fixed"
RelevanceOut = Literal["core", "foundation", "fixed"]

DepartmentName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NAME_LENGTH)
]


class PlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occupation: Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_NAME_LENGTH)]
    grade: int = Field(strict=True, ge=min(ALL_GRADES), le=max(ALL_GRADES))
    term: Term | None = None
    department: DepartmentName
    chosen_classes: dict[
        Annotated[str, StringConstraints(max_length=MAX_NAME_LENGTH)],
        Annotated[str, StringConstraints(max_length=MAX_NAME_LENGTH)],
    ] = Field(default_factory=dict, max_length=MAX_CHOSEN_CLASSES)
    fixed_courses: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NAME_LENGTH)
        ]
    ] = Field(default_factory=list, max_length=MAX_FIXED_COURSES)

    @field_validator("occupation")
    @classmethod
    def occupation_is_one_line(cls, occupation: str) -> str:
        if not is_single_line(occupation):
            raise ValueError("職業名は空でない 1 行にしてください")
        return occupation

    @field_validator("fixed_courses")
    @classmethod
    def fixed_courses_are_distinct(cls, names: list[str]) -> list[str]:
        if len(set(names)) != len(names):
            raise ValueError("先に入れる授業に同じ科目が 2 回あります")
        return names


class SlotOut(BaseModel):
    weekday: Weekday
    period: int


class CourseOut(BaseModel):
    name: str
    relevance: RelevanceOut
    reason: str
    prerequisite_for: str | None
    syllabus_code: str | None
    syllabus_url: str | None


class PlacedCourseOut(CourseOut):
    section_code: str
    class_code: str | None
    slots: list[SlotOut]
    room: str | None
    credits: int
    class_confirmed: bool


class SemesterPlanOut(BaseModel):
    grade: int
    term: Term
    credits: int
    courses: list[PlacedCourseOut]
    continuing: list[PlacedCourseOut]


class UnlinkedOut(BaseModel):
    name: str
    reason: str
    prerequisite_for: str | None


class ProfileOut(BaseModel):
    occupation: str
    interpretation: str
    assumption: str | None
    skills: list[str]


class ConditionsOut(BaseModel):
    occupation: str
    department: str
    year: int
    grade: int
    term: Term
    chosen_classes: dict[str, str]
    credit_limit: int
    fixed_courses: list[str]


class ResultOut(BaseModel):
    profile: ProfileOut
    semesters: list[SemesterPlanOut]
    unplaced: list[CourseOut]
    taken: list[CourseOut]
    offered_earlier: list[str]
    unlinked: list[UnlinkedOut]


class PlanOut(BaseModel):
    id: UUID
    status: PlanStatus
    stage: PlanStage | None
    conditions: ConditionsOut
    reading: ProfileOut | None
    result: ResultOut | None
    failure: str | None


class PlanSummaryOut(BaseModel):
    id: UUID
    status: PlanStatus
    occupation: str
    grade: int
    term: Term
    created_at: datetime


class PlanListOut(BaseModel):
    plans: list[PlanSummaryOut]
    total: int


def _course_out(course: PlannedCourse, links: PlanLinks) -> CourseOut:
    if isinstance(course, FixedCourse):
        return CourseOut(
            name=course.name,
            relevance=FIXED,
            reason="",
            prerequisite_for=None,
            syllabus_code=course.syllabus_code,
            syllabus_url=None
            if course.syllabus_code is None
            else links.urls.get(course.syllabus_code),
        )
    return CourseOut(
        name=course.name,
        relevance=course.relevance.value,
        reason=course.reason,
        prerequisite_for=course.prerequisite_for,
        syllabus_code=course.syllabus_code,
        syllabus_url=links.urls.get(course.syllabus_code),
    )


def _placed_out(placed: PlacedCourse, links: PlanLinks) -> PlacedCourseOut:
    section = placed.section
    course = _course_out(placed.course, links)
    page = links.page_of(section.code, course.syllabus_code)
    return PlacedCourseOut(
        **course.model_dump(exclude={"syllabus_code", "syllabus_url"}),
        syllabus_code=page,
        syllabus_url=None if page is None else links.urls.get(page),
        section_code=section.code,
        class_code=section.class_code,
        slots=[SlotOut(weekday=slot.weekday, period=slot.period) for slot in section.slots],
        room=section.room,
        credits=section.credits,
        class_confirmed=placed.class_confirmed,
    )


def plan_out(plan: Plan, links: PlanLinks) -> PlanOut:
    conditions = plan.conditions
    return PlanOut(
        id=plan.id,
        status=plan.status,
        stage=plan.stage,
        conditions=ConditionsOut(
            occupation=conditions.occupation,
            department=conditions.department,
            year=conditions.year,
            grade=conditions.start.grade,
            term=conditions.start.term,
            chosen_classes=dict(conditions.chosen_classes),
            credit_limit=conditions.credit_limit,
            fixed_courses=list(conditions.fixed_courses),
        ),
        reading=None if plan.reading is None else _profile_out(plan.reading),
        result=None if plan.result is None else _result_out(plan.result, links),
        failure=plan.failure,
    )


def _profile_out(profile: OccupationProfile) -> ProfileOut:
    return ProfileOut(
        occupation=profile.occupation,
        interpretation=profile.interpretation,
        assumption=profile.assumption,
        skills=list(profile.skills),
    )


def _result_out(result: PlanResult, links: PlanLinks) -> ResultOut:
    return ResultOut(
        profile=_profile_out(result.recommendation.profile),
        semesters=[
            SemesterPlanOut(
                grade=semester_plan.semester.grade,
                term=semester_plan.semester.term,
                credits=semester_plan.credits,
                courses=[_placed_out(placed, links) for placed in semester_plan.courses],
                continuing=[_placed_out(placed, links) for placed in semester_plan.continuing],
            )
            for semester_plan in result.roadmap.semesters
        ],
        unplaced=[_course_out(course, links) for course in result.roadmap.unplaced],
        taken=[_course_out(course, links) for course in result.roadmap.taken],
        offered_earlier=sorted(result.roadmap.offered_earlier),
        unlinked=[
            UnlinkedOut(
                name=choice.name, reason=choice.reason, prerequisite_for=choice.prerequisite_for
            )
            for choice in result.recommendation.unlinked
        ],
    )
