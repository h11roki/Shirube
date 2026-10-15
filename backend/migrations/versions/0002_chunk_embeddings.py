from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "embeddings",
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("vector", Vector(1536), nullable=False),
        sa.PrimaryKeyConstraint("model", "content_hash"),
    )
    op.create_table(
        "syllabus_chunks",
        sa.Column("year", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("syllabus_code", sa.Text(), nullable=False),
        sa.Column("section", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["year", "syllabus_code"], ["syllabi.year", "syllabi.code"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("year", "syllabus_code", "section"),
    )
    op.create_index(
        "ix_syllabus_chunks_content_hash", "syllabus_chunks", ["content_hash"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_syllabus_chunks_content_hash", table_name="syllabus_chunks")
    op.drop_table("syllabus_chunks")
    op.drop_table("embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")
