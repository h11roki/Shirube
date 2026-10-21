from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("plans", "conditions", nullable=True)
    op.alter_column("plans", "user_id", nullable=True)
    op.drop_constraint("ck_plans_status", "plans", type_="check")
    op.create_check_constraint(
        "ck_plans_status",
        "plans",
        "status IN ('pending', 'running', 'succeeded', 'failed', 'deleted')",
    )
    op.create_check_constraint(
        "ck_plans_conditions", "plans", "(status = 'deleted') = (conditions IS NULL)"
    )
    op.create_check_constraint(
        "ck_plans_owner", "plans", "user_id IS NOT NULL OR status = 'deleted'"
    )
    op.create_index(
        "ix_plans_deleted",
        "plans",
        ["created_at"],
        postgresql_where=sa.text("status = 'deleted'"),
    )
    op.drop_constraint("fk_plans_user_id_users", "plans", type_="foreignkey")
    op.create_foreign_key(
        "fk_plans_user_id_users", "plans", "users", ["user_id"], ["id"], ondelete="SET NULL"
    )
    op.drop_constraint("fk_taken_courses_user_id_users", "taken_courses", type_="foreignkey")
    op.create_foreign_key(
        "fk_taken_courses_user_id_users",
        "taken_courses",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_taken_courses_user_id_users", "taken_courses", type_="foreignkey")
    op.create_foreign_key(
        "fk_taken_courses_user_id_users", "taken_courses", "users", ["user_id"], ["id"]
    )
    op.drop_constraint("fk_plans_user_id_users", "plans", type_="foreignkey")
    op.create_foreign_key("fk_plans_user_id_users", "plans", "users", ["user_id"], ["id"])
    op.drop_index(
        "ix_plans_deleted", table_name="plans", postgresql_where=sa.text("status = 'deleted'")
    )
    op.execute("DELETE FROM plans WHERE status = 'deleted'")
    op.drop_constraint("ck_plans_owner", "plans", type_="check")
    op.drop_constraint("ck_plans_conditions", "plans", type_="check")
    op.drop_constraint("ck_plans_status", "plans", type_="check")
    op.create_check_constraint(
        "ck_plans_status", "plans", "status IN ('pending', 'running', 'succeeded', 'failed')"
    )
    op.alter_column("plans", "user_id", nullable=False)
    op.alter_column("plans", "conditions", nullable=False)
