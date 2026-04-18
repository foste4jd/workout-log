from datetime import datetime, timezone
from backend.db.database import db


class Program(db.Model):
    __tablename__ = "programs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    total_weeks = db.Column(db.Integer, nullable=False, default=4)
    start_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    days = db.relationship(
        "ProgramDay",
        backref="program",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ProgramDay.week_number, ProgramDay.day_order",
    )

    def to_dict(self, include_days=False):
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "total_weeks": self.total_weeks,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_days:
            result["days"] = [day.to_dict() for day in self.days]
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
