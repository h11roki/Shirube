from typing import TypedDict

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKeyConstraint, Index, Text
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
