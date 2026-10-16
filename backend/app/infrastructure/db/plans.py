from collections.abc import Mapping
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import Engine
from sqlalchemy.orm import Session as DbSession

from app.application.ports import PlanFormatError
from app.domain.course import Term
from app.domain.occupation import OccupationProfile
from app.domain.plan import Plan, PlanConditions
from app.domain.recommendation import CourseChoice, Recommendation, RecommendedCourse, Relevance
from app.domain.roadmap import PlacedCourse, Roadmap, Semester, SemesterPlan
from app.infrastructure.db.courses import section_from_json, section_json
from app.infrastructure.db.models import (
    ChoiceJson,
    ConditionsJson,
    PlacedJson,
    PlanJson,
    PlanRow,
    ProfileJson,
    RecommendationJson,
    RecommendedJson,
    RoadmapJson,
    SemesterJson,
    SemesterPlanJson,
)

PLAN_JSON_VERSION = 1
PLAN_JSON = TypeAdapter(PlanJson)


class SqlPlanRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, plan: Plan) -> None:
        with DbSession(self._engine) as db, db.begin():
            db.add(PlanRow(id=plan.id, body=plan_json(plan)))

    def get(self, plan_id: UUID) -> Plan | None:
        with DbSession(self._engine) as db:
            row = db.get(PlanRow, plan_id)
        if row is None:
            return None
        version = row.body.get("version") if isinstance(row.body, dict) else None
        if version != PLAN_JSON_VERSION:
            raise PlanFormatError(f"{plan_id}: 読めない版の Plan です: {version}")
        try:
            return plan_from_json(plan_id, PLAN_JSON.validate_python(row.body, strict=True))
        except (KeyError, ValueError) as error:
            raise PlanFormatError(f"{plan_id}: 保存した Plan を読めません: {error!r}") from error


def _semester_json(semester: Semester) -> SemesterJson:
    return SemesterJson(grade=semester.grade, term=semester.term.value)


def _semester(data: SemesterJson) -> Semester:
    return Semester(data["grade"], Term(data["term"]))


def _placed_json(placed: PlacedCourse) -> PlacedJson:
    return PlacedJson(
        course=placed.course.name,
        section=section_json(placed.section),
        class_confirmed=placed.class_confirmed,
    )


def _placed(data: PlacedJson, courses: Mapping[str, RecommendedCourse]) -> PlacedCourse:
    return PlacedCourse(
        courses[data["course"]], section_from_json(data["section"]), data["class_confirmed"]
    )


def plan_json(plan: Plan) -> PlanJson:
    conditions = plan.conditions
    recommendation = plan.recommendation
    profile = recommendation.profile
    return PlanJson(
        version=PLAN_JSON_VERSION,
        conditions=ConditionsJson(
            occupation=conditions.occupation,
            department=conditions.department,
            year=conditions.year,
            start=_semester_json(conditions.start),
            chosen_classes=dict(conditions.chosen_classes),
            credit_limit=conditions.credit_limit,
        ),
        recommendation=RecommendationJson(
            profile=ProfileJson(
                occupation=profile.occupation,
                interpretation=profile.interpretation,
                assumption=profile.assumption,
                skills=list(profile.skills),
            ),
            courses=[
                RecommendedJson(
                    name=course.name,
                    syllabus_code=course.syllabus_code,
                    relevance=course.relevance.value,
                    reason=course.reason,
                    prerequisite_for=course.prerequisite_for,
                )
                for course in recommendation.courses
            ],
            candidates=list(recommendation.candidates),
            unlinked=[
                ChoiceJson(
                    name=choice.name,
                    relevance=choice.relevance.value,
                    reason=choice.reason,
                    prerequisite_for=choice.prerequisite_for,
                )
                for choice in recommendation.unlinked
            ],
        ),
        roadmap=RoadmapJson(
            semesters=[
                SemesterPlanJson(
                    semester=_semester_json(semester_plan.semester),
                    courses=[_placed_json(placed) for placed in semester_plan.courses],
                    continuing=[placed.course.name for placed in semester_plan.continuing],
                )
                for semester_plan in plan.roadmap.semesters
            ],
            unplaced=[course.name for course in plan.roadmap.unplaced],
        ),
    )


def plan_from_json(plan_id: UUID, data: PlanJson) -> Plan:
    conditions = data["conditions"]
    stored = data["recommendation"]
    profile = stored["profile"]
    recommendation = Recommendation(
        OccupationProfile(
            profile["occupation"],
            profile["interpretation"],
            profile["assumption"],
            tuple(profile["skills"]),
        ),
        tuple(
            RecommendedCourse(
                course["name"],
                course["syllabus_code"],
                Relevance(course["relevance"]),
                course["reason"],
                course["prerequisite_for"],
            )
            for course in stored["courses"]
        ),
        tuple(stored["candidates"]),
        tuple(
            CourseChoice(
                choice["name"],
                Relevance(choice["relevance"]),
                choice["reason"],
                choice["prerequisite_for"],
            )
            for choice in stored["unlinked"]
        ),
    )
    courses = {course.name: course for course in recommendation.courses}
    placed_by_grade: dict[tuple[int, str], PlacedCourse] = {}
    semester_plans = []
    for stored_plan in data["roadmap"]["semesters"]:
        semester = _semester(stored_plan["semester"])
        placed = tuple(_placed(item, courses) for item in stored_plan["courses"])
        placed_by_grade.update(((semester.grade, item.course.name), item) for item in placed)
        continuing = tuple(
            placed_by_grade[(semester.grade, name)] for name in stored_plan["continuing"]
        )
        semester_plans.append(SemesterPlan(semester, placed, continuing))
    roadmap = Roadmap(
        tuple(semester_plans), tuple(courses[name] for name in data["roadmap"]["unplaced"])
    )
    return Plan(
        plan_id,
        PlanConditions(
            conditions["occupation"],
            conditions["department"],
            conditions["year"],
            _semester(conditions["start"]),
            tuple(sorted(conditions["chosen_classes"].items())),
            conditions["credit_limit"],
        ),
        recommendation,
        roadmap,
    )
