import json
from datetime import datetime, timezone
from backend.db.database import db


class AIKnowledge(db.Model):
    __tablename__ = "ai_knowledge"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type         = db.Column(db.String(20), nullable=False, default="memory")
    # schedule | recovery | injury | preferences | performance_pattern | other
    category     = db.Column(db.String(40), nullable=False)
    text         = db.Column(db.Text, nullable=False)
    priority     = db.Column(db.String(10), default="medium")   # low | medium | high
    # user_prompt | workout_note | detected_pattern | web_reference
    source_type  = db.Column(db.String(40), nullable=True)
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at   = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_used_at = db.Column(db.DateTime, nullable=True)
    meta         = db.Column(db.Text, nullable=True)  # JSON blob for extra context

    def get_meta(self):
        if self.meta:
            try:
                return json.loads(self.meta)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def to_dict(self):
        return {
            "id":           self.id,
            "user_id":      self.user_id,
            "type":         self.type,
            "category":     self.category,
            "text":         self.text,
            "priority":     self.priority,
            "source_type":  self.source_type,
            "is_active":    self.is_active,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "updated_at":   self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
