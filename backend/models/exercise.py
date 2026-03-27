from backend.db.database import db


class Exercise(db.Model):
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey("workouts.id"), nullable=False)
    # FK to canonical library; nullable so old free-text exercises still work
    exercise_library_id = db.Column(db.Integer, db.ForeignKey("exercise_library.id"), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text)
    set_records = db.relationship(
        "ExerciseSet",
        backref="exercise",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="ExerciseSet.set_number",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "workout_id": self.workout_id,
            "exercise_library_id": self.exercise_library_id,
            "name": self.name,
            "notes": self.notes,
            "sets": [s.to_dict() for s in self.set_records],
        }