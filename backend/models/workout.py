from datetime import datetime, timezone
from backend.db.database import db


class Workout(db.Model):
    __tablename__ = "workouts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # planned | in_progress | completed
    status = db.Column(db.String(20), nullable=False, default="completed")
    # set when created from a template (informational only — session is a snapshot)
    template_id = db.Column(db.Integer, db.ForeignKey("workout_templates.id", ondelete="SET NULL"), nullable=True)
    # set when created by a program run — nulled when run is deleted
    program_run_id = db.Column(db.Integer, db.ForeignKey("program_runs.id", ondelete="SET NULL"), nullable=True)
    program_day_id = db.Column(db.Integer, db.ForeignKey("program_days.id", ondelete="SET NULL"), nullable=True)
    exercises = db.relationship("Exercise", backref="workout", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "notes": self.notes,
            "duration_minutes": self.duration_minutes,
            "date": self.date.isoformat(),
            "status": self.status,
            "template_id": self.template_id,
            "program_run_id": self.program_run_id,
            "program_day_id": self.program_day_id,
        }
