from datetime import datetime, timezone
from backend.db.database import db


class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    # Training configuration — each field is nullable (not-yet-set is valid state)
    experience_level = db.Column(db.String(20))          # beginner/intermediate/advanced/elite
    primary_goal = db.Column(db.String(30))              # strength/hypertrophy/powerlifting/general/endurance
    training_frequency_target = db.Column(db.Integer)    # days per week, 1–7
    preferred_intensity_style = db.Column(db.String(20)) # rpe/percentage/load/auto
    movement_restrictions = db.Column(db.Text)

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "experience_level": self.experience_level,
            "primary_goal": self.primary_goal,
            "training_frequency_target": self.training_frequency_target,
            "preferred_intensity_style": self.preferred_intensity_style,
            "movement_restrictions": self.movement_restrictions,
        }
