"""add program_runs table and workout FK columns

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Create program_runs if not already created by db.create_all()
    exists = bind.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='program_runs'")
    ).fetchone()
    if not exists:
        op.create_table(
            "program_runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("program_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("training_days", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    # Add program_run_id to workouts if missing
    cols = {c["name"] for c in sa.inspect(bind).get_columns("workouts")}
    if "program_run_id" not in cols:
        op.add_column("workouts", sa.Column("program_run_id", sa.Integer(), nullable=True))
    if "program_day_id" not in cols:
        op.add_column("workouts", sa.Column("program_day_id", sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("workouts")}
    if "program_day_id" in cols:
        op.drop_column("workouts", "program_day_id")
    if "program_run_id" in cols:
        op.drop_column("workouts", "program_run_id")
    op.drop_table("program_runs")
