from backend.db.database import db

SET_TYPES = ("warmup", "working", "amrap", "emom", "failure")


class ExerciseSet(db.Model):
    __tablename__ = "exercise_sets"

    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    set_number = db.Column(db.Integer, nullable=False)
    # warmup | working | amrap | emom | failure
    set_type = db.Column(db.String(20), nullable=False, default="working")
    # Planned values — populated from template or copied session; null on ad-hoc sets
    planned_reps = db.Column(db.Integer)
    planned_weight_lb = db.Column(db.Float)
    planned_percent = db.Column(db.Float)
    # Actual logged values — null until the set is performed
    reps = db.Column(db.Integer)
    weight_lb = db.Column(db.Float)
    percent = db.Column(db.Float)
    duration_seconds = db.Column(db.Integer)
    completed = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "exercise_id": self.exercise_id,
            "set_number": self.set_number,
            "set_type": self.set_type,
            "planned_reps": self.planned_reps,
            "planned_weight_lb": self.planned_weight_lb,
            "planned_percent": self.planned_percent,
            "reps": self.reps,
            "weight_lb": self.weight_lb,
            "percent": self.percent,
            "duration_seconds": self.duration_seconds,
            "completed": self.completed,
        }
