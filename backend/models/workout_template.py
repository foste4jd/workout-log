from datetime import datetime, timezone
from backend.db.database import db


class WorkoutTemplate(db.Model):
    __tablename__ = "workout_templates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    exercises = db.relationship(
        "WorkoutTemplateExercise",
        backref="template",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="WorkoutTemplateExercise.order_index",
    )

    def to_dict(self, include_exercises=False):
        d = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_exercises:
            d["exercises"] = [e.to_dict() for e in self.exercises]
        return d


class WorkoutTemplateExercise(db.Model):
    __tablename__ = "workout_template_exercises"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("workout_templates.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercise_library.id"), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text)

    exercise = db.relationship("ExerciseLibrary", lazy="joined")
    sets = db.relationship(
        "WorkoutTemplateSet",
        backref="template_exercise",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="WorkoutTemplateSet.set_number",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "exercise_id": self.exercise_id,
            "exercise_name": self.exercise.name if self.exercise else None,
            "order_index": self.order_index,
            "notes": self.notes,
            "sets": [s.to_dict() for s in self.sets],
        }


class WorkoutTemplateSet(db.Model):
    __tablename__ = "workout_template_sets"

    id = db.Column(db.Integer, primary_key=True)
    template_exercise_id = db.Column(
        db.Integer, db.ForeignKey("workout_template_exercises.id"), nullable=False
    )
    set_number = db.Column(db.Integer, nullable=False)
    set_type = db.Column(db.String(20), nullable=False, default="working")
    reps = db.Column(db.Integer)
    weight = db.Column(db.Float)
    percent = db.Column(db.Float)
    duration_seconds = db.Column(db.Integer)

    def to_dict(self):
        return {
            "id": self.id,
            "set_number": self.set_number,
            "set_type": self.set_type,
            "reps": self.reps,
            "weight": self.weight,
            "percent": self.percent,
            "duration_seconds": self.duration_seconds,
        }
