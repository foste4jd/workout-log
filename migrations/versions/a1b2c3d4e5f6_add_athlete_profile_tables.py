"""add user_profiles and bodyweight_entries tables

Revision ID: a1b2c3d4e5f6
Revises: f3a9c2b1d5e7
Create Date: 2026-04-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'f3a9c2b1d5e7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing = bind.execute(
        __import__('sqlalchemy', fromlist=['text']).text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'"
        )
    ).fetchone()
    if existing:
        return  # tables already created by db.create_all() on first boot

    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('experience_level', sa.String(length=20), nullable=True),
        sa.Column('primary_goal', sa.String(length=30), nullable=True),
        sa.Column('training_frequency_target', sa.Integer(), nullable=True),
        sa.Column('preferred_intensity_style', sa.String(length=20), nullable=True),
        sa.Column('movement_restrictions', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_table(
        'bodyweight_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('recorded_date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('bodyweight_entries')
    op.drop_table('user_profiles')
