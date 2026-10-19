from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "taken_courses",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_taken_courses_user_id_users"),
        sa.PrimaryKeyConstraint("user_id", "name"),
    )
    op.execute(
        """
        UPDATE plans SET result = jsonb_set(
            jsonb_set(result, '{roadmap,taken}', '[]'),
            '{roadmap,offered_earlier}',
            '[]'
        ) || jsonb_build_object('version', 3)
        WHERE result ->> 'version' = '2'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE plans SET result = jsonb_set(
            result #- '{roadmap,taken}' #- '{roadmap,offered_earlier}',
            '{roadmap,unplaced}',
            (result #> '{roadmap,unplaced}') || (result #> '{roadmap,taken}')
        ) || jsonb_build_object('version', 2)
        WHERE result ->> 'version' = '3'
        """
    )
    op.drop_table("taken_courses")
