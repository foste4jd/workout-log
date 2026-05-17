"""exercise_library_v3: add tier, parent; re-seed equipment as JSON array

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("exercise_library", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tier", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("parent", sa.String(120), nullable=True))

    # Convert existing equipment string values to JSON arrays so the ORM's JSON
    # type can deserialize them. Rows where equipment already starts with '[' are
    # already JSON and must not be double-wrapped.
    op.execute(
        "UPDATE exercise_library "
        "SET equipment = json_array(equipment) "
        "WHERE equipment IS NOT NULL "
        "  AND equipment != '' "
        "  AND substr(equipment, 1, 1) != '['"
    )
    op.execute(
        "UPDATE exercise_library "
        "SET equipment = '[]' "
        "WHERE equipment IS NULL OR equipment = ''"
    )


def downgrade():
    with op.batch_alter_table("exercise_library", schema=None) as batch_op:
        batch_op.drop_column("tier")
        batch_op.drop_column("parent")
