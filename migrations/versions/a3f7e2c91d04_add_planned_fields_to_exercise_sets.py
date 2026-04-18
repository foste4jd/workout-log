"""add planned fields to exercise_sets

Revision ID: a3f7e2c91d04
Revises: 0b36035b6e36
Create Date: 2026-04-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a3f7e2c91d04'
down_revision = '0b36035b6e36'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('exercise_sets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('planned_reps', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('planned_weight_lb', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('planned_percent', sa.Float(), nullable=True))
        batch_op.alter_column('completed', server_default=sa.false())


def downgrade():
    with op.batch_alter_table('exercise_sets', schema=None) as batch_op:
        batch_op.drop_column('planned_percent')
        batch_op.drop_column('planned_weight_lb')
        batch_op.drop_column('planned_reps')
