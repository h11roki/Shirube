from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NAME = "item #>> '{}'"
NAME_OF_PLACED = "item ->> 'course'"


def upgrade() -> None:
    op.execute(
        """
        UPDATE plans SET conditions = conditions || '{"fixed_courses": []}'
        WHERE NOT conditions ? 'fixed_courses'
        """
    )
    op.execute(
        """
        UPDATE plans SET result = jsonb_set(result, '{roadmap,fixed}', '[]')
            || jsonb_build_object('version', 4)
        WHERE result ->> 'version' = '3'
        """
    )


def without_fixed(items: str, name_of_item: str) -> str:
    return f"""(
        SELECT COALESCE(jsonb_agg(item ORDER BY item_ordinal), '[]')
        FROM jsonb_array_elements({items}) WITH ORDINALITY AS items(item, item_ordinal)
        WHERE NOT (named.fixed_names ? ({name_of_item}))
    )"""


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE plans SET result = result || jsonb_build_object(
            'version', 3,
            'roadmap', ((result -> 'roadmap') - 'fixed') || jsonb_build_object(
                'semesters', (
                    SELECT COALESCE(jsonb_agg(
                        semester || jsonb_build_object(
                            'courses', {without_fixed("semester -> 'courses'", NAME_OF_PLACED)},
                            'continuing', {without_fixed("semester -> 'continuing'", NAME)}
                        ) ORDER BY semester_ordinal
                    ), '[]')
                    FROM jsonb_array_elements(result -> 'roadmap' -> 'semesters')
                        WITH ORDINALITY AS semesters(semester, semester_ordinal)
                ),
                'unplaced', {without_fixed("result -> 'roadmap' -> 'unplaced'", NAME)}
            )
        )
        FROM (
            SELECT id, (
                SELECT COALESCE(jsonb_agg(fixed -> 'name'), '[]')
                FROM jsonb_array_elements(result -> 'roadmap' -> 'fixed') AS fixed
            ) AS fixed_names
            FROM plans WHERE result ->> 'version' = '4'
        ) AS named
        WHERE plans.id = named.id
        """
    )
    op.execute("UPDATE plans SET conditions = conditions - 'fixed_courses'")
