from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("syllabi", sa.Column("url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("syllabi", "url")
