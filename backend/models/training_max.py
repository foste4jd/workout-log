from datetime import datetime, timezone
from backend.db.database import db


class TrainingMax(db.Model):
    __tablename__ = "training_maxes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercise_library.id"), nullable=False)
    training_max_weight = db.Column(db.Float, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    notes = db.Column(db.Text)

    exercise = db.relationship("ExerciseLibrary", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint("user_id", "exercise_id", name="uq_training_max_user_exercise"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "exercise_id": self.exercise_id,
            "exercise_name": self.exercise.name if self.exercise else None,
            "training_max_weight": self.training_max_weight,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "notes": self.notes,
        }
