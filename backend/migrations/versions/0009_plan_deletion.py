from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deleted_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_deleted_plans_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deleted_plans")),
    )
    op.create_index(
        op.f("ix_deleted_plans_created_at"), "deleted_plans", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_deleted_plans_user_id"), "deleted_plans", ["user_id"], unique=False)
    op.drop_constraint("fk_plans_user_id_users", "plans", type_="foreignkey")
    op.create_foreign_key(
        "fk_plans_user_id_users", "plans", "users", ["user_id"], ["id"], ondelete="CASCADE"
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
    op.drop_index(op.f("ix_deleted_plans_user_id"), table_name="deleted_plans")
    op.drop_index(op.f("ix_deleted_plans_created_at"), table_name="deleted_plans")
    op.drop_table("deleted_plans")
