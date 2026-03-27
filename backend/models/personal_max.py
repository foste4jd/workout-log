from backend.db.database import db


class PersonalMax(db.Model):
    __tablename__ = "personal_maxes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exercise_name = db.Column(db.String(120), nullable=False)
    weight_lb = db.Column(db.Float, nullable=False)
    is_manual = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "exercise_name", name="uq_user_exercise"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "exercise_name": self.exercise_name,
            "weight_lb": self.weight_lb,
        }