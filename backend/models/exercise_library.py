from backend.db.database import db


class ExerciseLibrary(db.Model):
    __tablename__ = "exercise_library"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    # compound | accessory
    category = db.Column(db.String(60), nullable=True)
    aliases = db.Column(db.JSON, nullable=False, default=list)
    primary_muscle = db.Column(db.String(60), nullable=True)
    secondary_muscles = db.Column(db.JSON, nullable=False, default=list)
    # JSON array of equipment strings, e.g. ["dumbbell", "kettlebell"]
    equipment = db.Column(db.JSON, nullable=False, default=list)
    movement_pattern = db.Column(db.String(40), nullable=True)
    unilateral = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_custom = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=500)
    # core | secondary | optional
    tier = db.Column(db.String(20), nullable=True)
    # canonical name of the parent exercise (for variations)
    parent = db.Column(db.String(120), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "tier": self.tier,
            "parent": self.parent,
            "aliases": self.aliases or [],
            "primary_muscle": self.primary_muscle,
            "secondary_muscles": self.secondary_muscles or [],
            "equipment": self.equipment or [],
            "movement_pattern": self.movement_pattern,
            "unilateral": self.unilateral,
            "is_active": self.is_active,
            "is_custom": self.is_custom,
        }
