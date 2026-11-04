from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_builds",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column(
            "cause_types",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("cause_code", sa.Text(), nullable=True),
        sa.Column("queued_seconds", sa.Double(), nullable=True),
        sa.Column("seconds", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "outcome <> 'failed' OR cardinality(cause_types) > 0", name="ck_plan_builds_cause"
        ),
        sa.CheckConstraint(
            "outcome IN ('succeeded', 'failed', 'discarded', 'stalled')",
            name="ck_plan_builds_outcome",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plan_builds_finished_at"), "plan_builds", ["finished_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_plan_builds_finished_at"), table_name="plan_builds")
    op.drop_table("plan_builds")
