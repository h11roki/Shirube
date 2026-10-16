from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.course import ALL_GRADES
from app.domain.occupation import is_single_line
from app.domain.plan import Plan
from app.domain.recommendation import RecommendedCourse
from app.domain.roadmap import PlacedCourse

TermName = Literal["spring", "autumn"]
RelevanceName = Literal["core", "foundation"]


class PlanIn(BaseModel):
    occupation: str = Field(max_length=100)
    grade: int = Field(ge=min(ALL_GRADES), le=max(ALL_GRADES))
    term: TermName | None = None
    department: str = Field(min_length=1)
    chosen_classes: dict[str, str] = Field(default_factory=dict)

    @field_validator("occupation")
    @classmethod
    def occupation_is_one_line(cls, occupation: str) -> str:
        if not is_single_line(occupation):
            raise ValueError("職業名は空でない 1 行にしてください")
        return occupation.strip()


class SlotOut(BaseModel):
    weekday: str
    period: int


class CourseOut(BaseModel):
    name: str
    relevance: RelevanceName
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
    term: TermName
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
    term: TermName
    chosen_classes: dict[str, str]
    credit_limit: int


class PlanOut(BaseModel):
    id: UUID
    conditions: ConditionsOut
    profile: ProfileOut
    semesters: list[SemesterPlanOut]
    unplaced: list[CourseOut]
    unlinked: list[UnlinkedOut]


def _course_out(course: RecommendedCourse) -> CourseOut:
    return CourseOut(
        name=course.name,
        relevance=course.relevance.value,
        reason=course.reason,
        prerequisite_for=course.prerequisite_for,
        syllabus_code=course.syllabus_code,
    )


def _placed_out(placed: PlacedCourse) -> PlacedCourseOut:
    section = placed.section
    return PlacedCourseOut(
        **_course_out(placed.course).model_dump(),
        section_code=section.code,
        class_code=section.class_code,
        slots=[SlotOut(weekday=slot.weekday.value, period=slot.period) for slot in section.slots],
        credits=section.credits,
        class_confirmed=placed.class_confirmed,
    )


def plan_out(plan: Plan) -> PlanOut:
    conditions = plan.conditions
    profile = plan.recommendation.profile
    return PlanOut(
        id=plan.id,
        conditions=ConditionsOut(
            occupation=conditions.occupation,
            department=conditions.department,
            year=conditions.year,
            grade=conditions.start.grade,
            term=conditions.start.term.value,
            chosen_classes=dict(conditions.chosen_classes),
            credit_limit=conditions.credit_limit,
        ),
        profile=ProfileOut(
            occupation=profile.occupation,
            interpretation=profile.interpretation,
            assumption=profile.assumption,
            skills=list(profile.skills),
        ),
        semesters=[
            SemesterPlanOut(
                grade=semester_plan.semester.grade,
                term=semester_plan.semester.term.value,
                credits=semester_plan.credits,
                courses=[_placed_out(placed) for placed in semester_plan.courses],
                continuing=[_placed_out(placed) for placed in semester_plan.continuing],
            )
            for semester_plan in plan.roadmap.semesters
        ],
        unplaced=[_course_out(course) for course in plan.roadmap.unplaced],
        unlinked=[
            UnlinkedOut(
                name=choice.name, reason=choice.reason, prerequisite_for=choice.prerequisite_for
            )
            for choice in plan.recommendation.unlinked
        ],
    )
