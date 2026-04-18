"""add timezone to users

Revision ID: f3a9c2b1d5e7
Revises: 6d29d6812665
Create Date: 2026-04-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f3a9c2b1d5e7'
down_revision = '6d29d6812665'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timezone', sa.String(length=60), nullable=False, server_default='UTC'))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('timezone')