from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "course_sections",
        sa.Column("year", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("class_code", sa.Text(), nullable=True),
        sa.Column("term", sa.Text(), nullable=True),
        sa.Column("slots", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("departments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("audiences", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("instructors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("room", sa.Text(), nullable=True),
        sa.Column("registration", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("year", "code"),
    )
    op.create_table(
        "syllabi",
        sa.Column("year", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("term_label", sa.Text(), nullable=False),
        sa.Column("slot_label", sa.Text(), nullable=False),
        sa.Column("faculties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("instructors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("campus", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("objectives", sa.Text(), nullable=False),
        sa.Column("preparation", sa.Text(), nullable=False),
        sa.Column("schedule_note", sa.Text(), nullable=False),
        sa.Column("sessions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("class_format", sa.Text(), nullable=False),
        sa.Column("self_study", sa.Text(), nullable=False),
        sa.Column("grading", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("grading_note", sa.Text(), nullable=False),
        sa.Column("advice", sa.Text(), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("year", "code"),
    )
    op.create_table(
        "syllabus_codes",
        sa.Column("year", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("syllabus_code", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["year", "syllabus_code"], ["syllabi.year", "syllabi.code"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("year", "code"),
    )


def downgrade() -> None:
    op.drop_table("syllabus_codes")
    op.drop_table("syllabi")
    op.drop_table("course_sections")
