from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.domain.course import ALL_GRADES, Term, Weekday
from app.domain.occupation import is_single_line
from app.domain.plan import Plan, PlanResult, PlanStage, PlanStatus
from app.domain.recommendation import RecommendedCourse, Relevance
from app.domain.roadmap import PlacedCourse

MAX_CHOSEN_CLASSES = 50
MAX_TAKEN_COURSES = 50
MAX_NAME_LENGTH = 100

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

    @field_validator("occupation")
    @classmethod
    def occupation_is_one_line(cls, occupation: str) -> str:
        if not is_single_line(occupation):
            raise ValueError("職業名は空でない 1 行にしてください")
        return occupation


class TakenCoursesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    names: list[Annotated[str, StringConstraints(max_length=MAX_NAME_LENGTH)]] = Field(
        max_length=MAX_TAKEN_COURSES
    )


class SlotOut(BaseModel):
    weekday: Weekday
    period: int


class CourseOut(BaseModel):
    name: str
    relevance: Relevance
    reason: str
    prerequisite_for: str | None
    syllabus_code: str


class PlacedCourseOut(CourseOut):
    section_code: str
    class_code: str | None
    slots: list[SlotOut]
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


def _course_out(course: RecommendedCourse) -> CourseOut:
    return CourseOut(
        name=course.name,
        relevance=course.relevance,
        reason=course.reason,
        prerequisite_for=course.prerequisite_for,
        syllabus_code=course.syllabus_code,
    )


def _placed_out(placed: PlacedCourse) -> PlacedCourseOut:
    course = placed.course
    section = placed.section
    return PlacedCourseOut(
        name=course.name,
        relevance=course.relevance,
        reason=course.reason,
        prerequisite_for=course.prerequisite_for,
        syllabus_code=course.syllabus_code,
        section_code=section.code,
        class_code=section.class_code,
        slots=[SlotOut(weekday=slot.weekday, period=slot.period) for slot in section.slots],
        credits=section.credits,
        class_confirmed=placed.class_confirmed,
    )


def plan_out(plan: Plan) -> PlanOut:
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
        ),
        result=None if plan.result is None else _result_out(plan.result),
        failure=plan.failure,
    )


def _result_out(result: PlanResult) -> ResultOut:
    profile = result.recommendation.profile
    return ResultOut(
        profile=ProfileOut(
            occupation=profile.occupation,
            interpretation=profile.interpretation,
            assumption=profile.assumption,
            skills=list(profile.skills),
        ),
        semesters=[
            SemesterPlanOut(
                grade=semester_plan.semester.grade,
                term=semester_plan.semester.term,
                credits=semester_plan.credits,
                courses=[_placed_out(placed) for placed in semester_plan.courses],
                continuing=[_placed_out(placed) for placed in semester_plan.continuing],
            )
            for semester_plan in result.roadmap.semesters
        ],
        unplaced=[_course_out(course) for course in result.roadmap.unplaced],
        taken=[_course_out(course) for course in result.roadmap.taken],
        offered_earlier=sorted(result.roadmap.offered_earlier),
        unlinked=[
            UnlinkedOut(
                name=choice.name, reason=choice.reason, prerequisite_for=choice.prerequisite_for
            )
            for choice in result.recommendation.unlinked
        ],
    )
