import json
from datetime import datetime, timezone
from backend.db.database import db


class Program(db.Model):
    __tablename__ = "programs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    total_weeks = db.Column(db.Integer, nullable=False, default=4)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    days = db.relationship(
        "ProgramDay",
        backref="program",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ProgramDay.week_number, ProgramDay.day_order",
    )
    runs = db.relationship(
        "ProgramRun",
        backref="program",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_days=False, active_run=None):
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "total_weeks": self.total_weeks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_days:
            result["days"] = [day.to_dict() for day in self.days]
        if active_run is not None:
            result["active_run"] = active_run.to_dict() if active_run else None
        return result


class ProgramDay(db.Model):
    __tablename__ = "program_days"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)   # 1-based
    day_order = db.Column(db.Integer, nullable=False, default=1)  # ordering within the week
    template_id = db.Column(db.Integer, db.ForeignKey("workout_templates.id"), nullable=True)
    label = db.Column(db.String(80))

    template = db.relationship("WorkoutTemplate", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "week_number": self.week_number,
            "day_order": self.day_order,
            "template_id": self.template_id,
            "template_name": self.template.name if self.template else None,
            "label": self.label,
        }


class ProgramRun(db.Model):
    __tablename__ = "program_runs"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    training_days = db.Column(db.String(30), nullable=False)  # JSON array, e.g. "[1,3,5]"
    status = db.Column(db.String(20), nullable=False, default="active")  # active|completed|cancelled
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self, include_program=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "user_id": self.user_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "training_days": json.loads(self.training_days) if self.training_days else [],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_program and self.program:
            result["program"] = {
                "id": self.program.id,
                "name": self.program.name,
                "total_weeks": self.program.total_weeks,
                "description": self.program.description,
            }
        return result
