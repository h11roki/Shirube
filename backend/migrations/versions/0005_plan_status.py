from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("plans", "body", new_column_name="result", nullable=True)
    op.add_column("plans", sa.Column("status", sa.Text(), nullable=True))
    op.add_column(
        "plans",
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("plans", sa.Column("failure", sa.Text(), nullable=True))
    op.add_column("plans", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("plans", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE plans SET
            status = 'succeeded',
            conditions = result -> 'conditions',
            result = jsonb_build_object(
                'version', 2,
                'recommendation', result -> 'recommendation',
                'roadmap', result -> 'roadmap'
            ),
            finished_at = created_at
        WHERE result ->> 'version' = '1'
        """
    )
    op.alter_column("plans", "status", nullable=False)
    op.alter_column("plans", "conditions", nullable=False)
    op.create_check_constraint(
        "ck_plans_status", "plans", "status IN ('pending', 'running', 'succeeded', 'failed')"
    )
    op.create_check_constraint(
        "ck_plans_result", "plans", "(status = 'succeeded') = (result IS NOT NULL)"
    )
    op.create_check_constraint(
        "ck_plans_failure", "plans", "(status = 'failed') = (failure IS NOT NULL)"
    )
    op.create_index(
        "ix_plans_pending",
        "plans",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_plans_running",
        "plans",
        ["claimed_at"],
        unique=False,
        postgresql_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_index("ix_plans_running", table_name="plans")
    op.drop_index("ix_plans_pending", table_name="plans")
    op.drop_constraint("ck_plans_failure", "plans", type_="check")
    op.drop_constraint("ck_plans_result", "plans", type_="check")
    op.drop_constraint("ck_plans_status", "plans", type_="check")
    op.execute("DELETE FROM plans WHERE status <> 'succeeded'")
    op.execute(
        """
        UPDATE plans SET result = jsonb_build_object(
            'version', 1,
            'conditions', conditions,
            'recommendation', result -> 'recommendation',
            'roadmap', result -> 'roadmap'
        )
        """
    )
    op.drop_column("plans", "finished_at")
    op.drop_column("plans", "claimed_at")
    op.drop_column("plans", "failure")
    op.drop_column("plans", "conditions")
    op.drop_column("plans", "status")
    op.alter_column("plans", "result", new_column_name="body", nullable=False)
