from backend.db.database import db


class Exercise(db.Model):
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey("workouts.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight_kg = db.Column(db.Float)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "workout_id": self.workout_id,
            "name": self.name,
            "sets": self.sets,
            "reps": self.reps,
            "weight_kg": self.weight_kg,
            "notes": self.notes,
        }
