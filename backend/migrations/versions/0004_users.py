from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject"),
    )
    op.execute("DELETE FROM plans")
    op.add_column("plans", sa.Column("user_id", sa.Uuid(), nullable=False))
    op.create_index(op.f("ix_plans_user_id"), "plans", ["user_id"], unique=False)
    op.create_foreign_key("fk_plans_user_id_users", "plans", "users", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_plans_user_id_users", "plans", type_="foreignkey")
    op.drop_index(op.f("ix_plans_user_id"), table_name="plans")
    op.drop_column("plans", "user_id")
    op.drop_table("users")
