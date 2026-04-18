from datetime import datetime, timezone
from backend.db.database import db


class BodyweightEntry(db.Model):
    __tablename__ = "bodyweight_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    recorded_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self, unit="kg"):
        weight = self.weight_kg if unit == "kg" else round(self.weight_kg * 2.20462, 1)
        return {
            "id": self.id,
            "weight": weight,
            "weight_kg": self.weight_kg,
            "unit": unit,
            "recorded_date": str(self.recorded_date),
            "notes": self.notes,
        }
