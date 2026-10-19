from collections.abc import Mapping
from datetime import timedelta
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import ColumnElement, Engine, Select, func, select, update
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import aliased

from app.application.ports import PlanFormatError
from app.domain.course import Term
from app.domain.occupation import OccupationProfile
from app.domain.plan import (
    Plan,
    PlanConditions,
    PlanResult,
    PlanStage,
    PlanStatus,
    PlanSummary,
)
from app.domain.recommendation import CourseChoice, Recommendation, RecommendedCourse, Relevance
from app.domain.roadmap import PlacedCourse, Roadmap, Semester, SemesterPlan
from app.infrastructure.db.courses import section_from_json, section_json
from app.infrastructure.db.models import (
    ChoiceJson,
    ConditionsJson,
    PlacedJson,
    PlanRow,
    ProfileJson,
    RecommendationJson,
    RecommendedJson,
    ResultJson,
    RoadmapJson,
    SemesterJson,
    SemesterPlanJson,
)

RESULT_JSON_VERSION = 3
CONDITIONS_JSON = TypeAdapter(ConditionsJson)
RESULT_JSON = TypeAdapter(ResultJson)
FINISHED = frozenset({PlanStatus.SUCCEEDED, PlanStatus.FAILED})


class SqlPlanRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, plan: Plan) -> None:
        with DbSession(self._engine) as db, db.begin():
            db.add(
                PlanRow(
                    id=plan.id,
                    user_id=plan.owner_id,
                    status=plan.status,
                    conditions=conditions_json(plan.conditions),
                    result=None if plan.result is None else result_json(plan.result),
                    failure=plan.failure,
                    stage=plan.stage,
                )
            )

    def claim_next(self) -> Plan | None:
        pending = aliased(PlanRow)
        oldest = (
            select(pending.id)
            .where(pending.status == PlanStatus.PENDING)
            .order_by(pending.created_at, pending.id)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        return self._claim(PlanRow.id == oldest)

    def claim(self, plan_id: UUID) -> Plan | None:
        return self._claim(PlanRow.id == plan_id)

    def enter_stage(self, plan_id: UUID, stage: PlanStage) -> None:
        with DbSession(self._engine) as db, db.begin():
            db.execute(
                update(PlanRow)
                .where(PlanRow.id == plan_id, PlanRow.status == PlanStatus.RUNNING)
                .values(stage=stage)
                .execution_options(synchronize_session=False)
            )

    def finish(self, plan: Plan) -> bool:
        if plan.status not in FINISHED:
            raise ValueError(f"終わっていない道標は保存し直せません: {plan.status}")
        with DbSession(self._engine) as db, db.begin():
            finished = db.scalars(
                update(PlanRow)
                .where(PlanRow.id == plan.id, PlanRow.status == PlanStatus.RUNNING)
                .values(
                    status=plan.status,
                    result=None if plan.result is None else result_json(plan.result),
                    failure=plan.failure,
                    stage=None,
                    finished_at=func.now(),
                )
                .returning(PlanRow.id)
                .execution_options(synchronize_session=False)
            ).one_or_none()
        return finished is not None

    def replace_result(self, plan: Plan, previous: PlanResult) -> bool:
        if plan.result is None:
            raise ValueError(f"結果の無い道標は置き直せません: {plan.status}")
        with DbSession(self._engine) as db, db.begin():
            replaced = db.scalars(
                update(PlanRow)
                .where(
                    PlanRow.id == plan.id,
                    PlanRow.status == PlanStatus.SUCCEEDED,
                    PlanRow.result[("roadmap", "taken")]
                    == [course.name for course in previous.roadmap.taken],
                )
                .values(result=result_json(plan.result))
                .returning(PlanRow.id)
                .execution_options(synchronize_session=False)
            ).one_or_none()
        return replaced is not None

    def fail_stalled(self, after: timedelta, failure: str) -> list[UUID]:
        with DbSession(self._engine) as db, db.begin():
            return list(
                db.scalars(
                    update(PlanRow)
                    .where(
                        PlanRow.status == PlanStatus.RUNNING,
                        PlanRow.claimed_at < func.now() - after,
                    )
                    .values(
                        status=PlanStatus.FAILED,
                        failure=failure,
                        stage=None,
                        finished_at=func.now(),
                    )
                    .returning(PlanRow.id)
                    .execution_options(synchronize_session=False)
                )
            )

    def get(self, plan_id: UUID) -> Plan | None:
        return self._first(select(PlanRow).where(PlanRow.id == plan_id))

    def get_owned_by(self, plan_id: UUID, owner_id: UUID) -> Plan | None:
        return self._first(
            select(PlanRow).where(PlanRow.id == plan_id, PlanRow.user_id == owner_id)
        )

    def list_owned_by(self, owner_id: UUID, limit: int) -> list[PlanSummary]:
        with DbSession(self._engine) as db:
            rows = db.execute(
                select(PlanRow.id, PlanRow.status, PlanRow.conditions, PlanRow.created_at)
                .where(PlanRow.user_id == owner_id)
                .order_by(PlanRow.created_at.desc(), PlanRow.id.desc())
                .limit(limit)
            ).all()
        summaries = []
        for plan_id, status, stored, created_at in rows:
            conditions = _conditions(plan_id, stored)
            summaries.append(
                PlanSummary(
                    plan_id, PlanStatus(status), conditions.occupation, conditions.start, created_at
                )
            )
        return summaries

    def _claim(self, which: ColumnElement[bool]) -> Plan | None:
        with DbSession(self._engine, expire_on_commit=False) as db, db.begin():
            row = db.scalars(
                update(PlanRow)
                .where(which, PlanRow.status == PlanStatus.PENDING)
                .values(status=PlanStatus.RUNNING, stage=PlanStage.ANALYZING, claimed_at=func.now())
                .returning(PlanRow)
                .execution_options(synchronize_session=False)
            ).one_or_none()
        return None if row is None else _plan(row)

    def _first(self, query: Select[PlanRow]) -> Plan | None:
        with DbSession(self._engine) as db:
            row = db.scalars(query).one_or_none()
            return None if row is None else _plan(row)


def _plan(row: PlanRow) -> Plan:
    stored = row.result
    version = stored.get("version") if isinstance(stored, dict) else None
    if stored is not None and version != RESULT_JSON_VERSION:
        raise PlanFormatError(f"{row.id}: 読めない版の道標の結果です: {version}")
    conditions = _conditions(row.id, row.conditions)
    try:
        result = (
            None
            if stored is None
            else result_from_json(RESULT_JSON.validate_python(stored, strict=True))
        )
        return Plan(
            row.id,
            row.user_id,
            conditions,
            PlanStatus(row.status),
            result,
            row.failure,
            None if row.stage is None else PlanStage(row.stage),
        )
    except (KeyError, ValueError) as error:
        raise PlanFormatError(f"{row.id}: 保存した道標を読めません: {error!r}") from error


def _conditions(plan_id: UUID, stored: object) -> PlanConditions:
    try:
        return conditions_from_json(CONDITIONS_JSON.validate_python(stored, strict=True))
    except (KeyError, ValueError) as error:
        raise PlanFormatError(f"{plan_id}: 保存した道標を読めません: {error!r}") from error


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


def conditions_json(conditions: PlanConditions) -> ConditionsJson:
    return ConditionsJson(
        occupation=conditions.occupation,
        department=conditions.department,
        year=conditions.year,
        start=_semester_json(conditions.start),
        chosen_classes=dict(conditions.chosen_classes),
        credit_limit=conditions.credit_limit,
    )


def conditions_from_json(data: ConditionsJson) -> PlanConditions:
    return PlanConditions(
        data["occupation"],
        data["department"],
        data["year"],
        _semester(data["start"]),
        tuple(sorted(data["chosen_classes"].items())),
        data["credit_limit"],
    )


def result_json(result: PlanResult) -> ResultJson:
    recommendation = result.recommendation
    profile = recommendation.profile
    return ResultJson(
        version=RESULT_JSON_VERSION,
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
                for semester_plan in result.roadmap.semesters
            ],
            unplaced=[course.name for course in result.roadmap.unplaced],
            taken=[course.name for course in result.roadmap.taken],
            offered_earlier=sorted(result.roadmap.offered_earlier),
        ),
    )


def result_from_json(data: ResultJson) -> PlanResult:
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
    stored_roadmap = data["roadmap"]
    roadmap = Roadmap(
        tuple(semester_plans),
        tuple(courses[name] for name in stored_roadmap["unplaced"]),
        tuple(courses[name] for name in stored_roadmap["taken"]),
        frozenset(stored_roadmap["offered_earlier"]),
    )
    return PlanResult(recommendation, roadmap)
