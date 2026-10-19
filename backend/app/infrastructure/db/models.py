from datetime import datetime
from typing import TypedDict
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

EMBEDDING_DIMENSIONS = 1536


class SlotJson(TypedDict):
    weekday: str
    period: int


class AudienceJson(TypedDict):
    entry_year_from: int
    entry_year_to: int
    eligible_grades: list[int]
    category: str


class SectionJson(TypedDict):
    code: str
    name: str
    class_code: str | None
    term: str | None
    slots: list[SlotJson]
    departments: list[str] | None
    audiences: list[AudienceJson]
    credits: int
    instructors: list[str]
    room: str | None
    registration: str
    note: str | None


class SemesterJson(TypedDict):
    grade: int
    term: str


class ConditionsJson(TypedDict):
    occupation: str
    department: str
    year: int
    start: SemesterJson
    chosen_classes: dict[str, str]
    credit_limit: int


class ProfileJson(TypedDict):
    occupation: str
    interpretation: str
    assumption: str | None
    skills: list[str]


class ChoiceJson(TypedDict):
    name: str
    relevance: str
    reason: str
    prerequisite_for: str | None


class RecommendedJson(ChoiceJson):
    syllabus_code: str


class RecommendationJson(TypedDict):
    profile: ProfileJson
    courses: list[RecommendedJson]
    candidates: list[str]
    unlinked: list[ChoiceJson]


class PlacedJson(TypedDict):
    course: str
    section: SectionJson
    class_confirmed: bool


class SemesterPlanJson(TypedDict):
    semester: SemesterJson
    courses: list[PlacedJson]
    continuing: list[str]


class RoadmapJson(TypedDict):
    semesters: list[SemesterPlanJson]
    unplaced: list[str]
    taken: list[str]
    offered_earlier: list[str]


class ResultJson(TypedDict):
    version: int
    recommendation: RecommendationJson
    roadmap: RoadmapJson


class SessionJson(TypedDict):
    label: str
    theme: str
    keywords: str


class GradingJson(TypedDict):
    kind: str
    percentage: str
    criteria: str


class Base(DeclarativeBase):
    type_annotation_map = {str: Text()}


class CourseSectionRow(Base):
    __tablename__ = "course_sections"

    year: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    class_code: Mapped[str | None]
    term: Mapped[str | None]
    slots: Mapped[list[SlotJson]] = mapped_column(JSONB)
    departments: Mapped[list[str] | None] = mapped_column(JSONB(none_as_null=True))
    audiences: Mapped[list[AudienceJson]] = mapped_column(JSONB)
    credits: Mapped[int]
    instructors: Mapped[list[str]] = mapped_column(JSONB)
    room: Mapped[str | None]
    registration: Mapped[str]
    note: Mapped[str | None]


class SyllabusRow(Base):
    __tablename__ = "syllabi"

    year: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    term_label: Mapped[str]
    slot_label: Mapped[str]
    faculties: Mapped[list[str]] = mapped_column(JSONB)
    instructors: Mapped[list[str]] = mapped_column(JSONB)
    credits: Mapped[int]
    campus: Mapped[str]
    language: Mapped[str]
    overview: Mapped[str]
    objectives: Mapped[str]
    preparation: Mapped[str]
    schedule_note: Mapped[str]
    sessions: Mapped[list[SessionJson]] = mapped_column(JSONB)
    class_format: Mapped[str]
    self_study: Mapped[str]
    grading: Mapped[list[GradingJson]] = mapped_column(JSONB)
    grading_note: Mapped[str]
    advice: Mapped[str]
    remarks: Mapped[str]


class SyllabusCodeRow(Base):
    __tablename__ = "syllabus_codes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["year", "syllabus_code"], ["syllabi.year", "syllabi.code"], ondelete="CASCADE"
        ),
        Index("ix_syllabus_codes_year_syllabus_code", "year", "syllabus_code"),
    )

    year: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    syllabus_code: Mapped[str]
    position: Mapped[int]


class SyllabusChunkRow(Base):
    __tablename__ = "syllabus_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["year", "syllabus_code"], ["syllabi.year", "syllabi.code"], ondelete="CASCADE"
        ),
        Index("ix_syllabus_chunks_content_hash", "content_hash"),
    )

    year: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    syllabus_code: Mapped[str] = mapped_column(primary_key=True)
    section: Mapped[str] = mapped_column(primary_key=True)
    text: Mapped[str]
    content_hash: Mapped[str]


class EmbeddingRow(Base):
    __tablename__ = "embeddings"

    model: Mapped[str] = mapped_column(primary_key=True)
    content_hash: Mapped[str] = mapped_column(primary_key=True)
    vector: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TakenCourseRow(Base):
    __tablename__ = "taken_courses"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", name="fk_taken_courses_user_id_users"), primary_key=True
    )
    name: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlanRow(Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')", name="ck_plans_status"
        ),
        CheckConstraint("(status = 'succeeded') = (result IS NOT NULL)", name="ck_plans_result"),
        CheckConstraint("(status = 'failed') = (failure IS NOT NULL)", name="ck_plans_failure"),
        CheckConstraint(
            "stage IS NULL OR (status = 'running' "
            "AND stage IN ('analyzing', 'searching', 'selecting', 'placing'))",
            name="ck_plans_stage",
        ),
        Index("ix_plans_pending", "created_at", postgresql_where=text("status = 'pending'")),
        Index("ix_plans_running", "claimed_at", postgresql_where=text("status = 'running'")),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", name="fk_plans_user_id_users"), index=True
    )
    status: Mapped[str]
    conditions: Mapped[ConditionsJson] = mapped_column(JSONB)
    result: Mapped[ResultJson | None] = mapped_column(JSONB(none_as_null=True))
    failure: Mapped[str | None]
    stage: Mapped[str | None]
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
