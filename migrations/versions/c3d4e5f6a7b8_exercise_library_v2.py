"""exercise_library_v2: add aliases, muscles, equipment, movement_pattern, unilateral, sort_order

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("exercise_library") as batch_op:
        batch_op.add_column(sa.Column("aliases", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("primary_muscle", sa.String(60), nullable=True))
        batch_op.add_column(sa.Column("secondary_muscles", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("equipment", sa.String(60), nullable=True))
        batch_op.add_column(sa.Column("movement_pattern", sa.String(40), nullable=True))
        batch_op.add_column(sa.Column("unilateral", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("is_custom", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=True))
        # make legacy category column nullable so new seed rows don't need it
        batch_op.alter_column("category", existing_type=sa.String(60), nullable=True)

    op.execute("UPDATE exercise_library SET aliases = '[]', secondary_muscles = '[]', unilateral = 0, is_custom = 0, sort_order = 500")


def downgrade():
    with op.batch_alter_table("exercise_library") as batch_op:
        batch_op.drop_column("aliases")
        batch_op.drop_column("primary_muscle")
        batch_op.drop_column("secondary_muscles")
        batch_op.drop_column("equipment")
        batch_op.drop_column("movement_pattern")
        batch_op.drop_column("unilateral")
        batch_op.drop_column("is_custom")
        batch_op.drop_column("sort_order")
        batch_op.alter_column("category", existing_type=sa.String(60), nullable=False)
