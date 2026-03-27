from backend.db.database import db

SET_TYPES = ("warmup", "working", "amrap", "emom", "failure")


class ExerciseSet(db.Model):
    __tablename__ = "exercise_sets"

    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    set_number = db.Column(db.Integer, nullable=False)
    # warmup | working | amrap | emom | failure
    set_type = db.Column(db.String(20), nullable=False, default="working")
    reps = db.Column(db.Integer)
    weight_lb = db.Column(db.Float)
    # planned percentage of training max (stored, not recomputed)
    percent = db.Column(db.Float)
    duration_seconds = db.Column(db.Integer)
    completed = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "exercise_id": self.exercise_id,
            "set_number": self.set_number,
            "set_type": self.set_type,
            "reps": self.reps,
            "weight_lb": self.weight_lb,
            "percent": self.percent,
            "duration_seconds": self.duration_seconds,
            "completed": self.completed,
        }
