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
    template_id = db.Column(db.Integer, db.ForeignKey("workout_templates.id"), nullable=True)
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
        }
