from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plans", sa.Column("reading", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.create_check_constraint("ck_plans_reading", "plans", "reading IS NULL OR status = 'running'")


def downgrade() -> None:
    op.drop_constraint("ck_plans_reading", "plans", type_="check")
    op.drop_column("plans", "reading")
