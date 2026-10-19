from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("stage", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_plans_stage",
        "plans",
        "stage IS NULL OR (status = 'running' "
        "AND stage IN ('analyzing', 'searching', 'selecting', 'placing'))",
    )


def downgrade() -> None:
    op.drop_constraint("ck_plans_stage", "plans", type_="check")
    op.drop_column("plans", "stage")
