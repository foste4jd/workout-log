import os
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from sqlalchemy import text
from backend.config import Config
from backend.db.database import db

bcrypt = Bcrypt()
jwt = JWTManager()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(ROOT_DIR, "frontend", "templates"),
        static_folder=os.path.join(ROOT_DIR, "frontend", "static"),
    )
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # ── Import all models so SQLAlchemy registers them ────────────────────────
    from backend.models.user import User  # noqa: F401
    from backend.models.workout import Workout  # noqa: F401
    from backend.models.exercise import Exercise  # noqa: F401
    from backend.models.exercise_set import ExerciseSet  # noqa: F401
    from backend.models.personal_max import PersonalMax  # noqa: F401
    from backend.models.exercise_library import ExerciseLibrary  # noqa: F401
    from backend.models.training_max import TrainingMax  # noqa: F401
    from backend.models.workout_template import (  # noqa: F401
        WorkoutTemplate, WorkoutTemplateExercise, WorkoutTemplateSet
    )

    # ── Register blueprints ───────────────────────────────────────────────────
    from backend.api.routes.users import users_bp
    from backend.api.routes.workouts import workouts_bp
    from backend.api.routes.exercises import exercises_bp
    from backend.api.routes.views import views_bp
    from backend.api.routes.stats import stats_bp
    from backend.api.routes.maxes import maxes_bp
    from backend.api.routes.library import library_bp
    from backend.api.routes.training_maxes import training_maxes_bp
    from backend.api.routes.templates import templates_bp

    for bp in (
        users_bp, workouts_bp, exercises_bp, views_bp, stats_bp,
        maxes_bp, library_bp, training_maxes_bp, templates_bp,
    ):
        app.register_blueprint(bp)

    with app.app_context():
        db.create_all()
        _run_migrations()
        _seed_exercise_library()

    return app


# ── Schema migrations (SQLite ALTER TABLE) ────────────────────────────────────

def _run_migrations():
    """Add new columns to existing tables without Alembic.
    Each statement is wrapped in try/except so re-runs are safe."""
    migrations = [
        # Workout: status and template_id
        "ALTER TABLE workouts ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'completed'",
        "ALTER TABLE workouts ADD COLUMN template_id INTEGER REFERENCES workout_templates(id)",
        # Exercise: library foreign key
        "ALTER TABLE exercises ADD COLUMN exercise_library_id INTEGER REFERENCES exercise_library(id)",
        # ExerciseSet: new fields
        "ALTER TABLE exercise_sets ADD COLUMN set_type VARCHAR(20) NOT NULL DEFAULT 'working'",
        "ALTER TABLE exercise_sets ADD COLUMN percent FLOAT",
        "ALTER TABLE exercise_sets ADD COLUMN duration_seconds INTEGER",
        "ALTER TABLE exercise_sets ADD COLUMN completed BOOLEAN NOT NULL DEFAULT 1",
    ]
    with db.engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()


# ── Exercise library seed ─────────────────────────────────────────────────────

_LIBRARY = [
    # Squat
    ("Back Squat", "Squat"),
    ("Front Squat", "Squat"),
    ("Overhead Squat", "Squat"),
    ("Goblet Squat", "Squat"),
    ("Hack Squat", "Squat"),
    ("Box Squat", "Squat"),
    ("Bulgarian Split Squat", "Squat"),
    ("Pistol Squat", "Squat"),
    ("Sumo Squat", "Squat"),
    ("Lunge", "Squat"),
    ("Walking Lunge", "Squat"),
    ("Step-up", "Squat"),
    ("Box Step-up", "Squat"),
    ("Leg Press", "Squat"),
    # Hinge
    ("Deadlift", "Hinge"),
    ("Romanian Deadlift", "Hinge"),
    ("Sumo Deadlift", "Hinge"),
    ("Trap Bar Deadlift", "Hinge"),
    ("Good Morning", "Hinge"),
    ("Nordic Curl", "Hinge"),
    ("GHD Hamstring Curl", "Hinge"),
    ("GHD Back Extension", "Hinge"),
    ("Back Extension", "Hinge"),
    # Press
    ("Bench Press", "Press"),
    ("Incline Bench Press", "Press"),
    ("Decline Bench Press", "Press"),
    ("Close-Grip Bench Press", "Press"),
    ("Overhead Press", "Press"),
    ("Arnold Press", "Press"),
    ("Dumbbell Bench Press", "Press"),
    ("Seated Dumbbell Press", "Press"),
    ("Machine Shoulder Press", "Press"),
    ("Push-up", "Press"),
    ("Diamond Push-up", "Press"),
    ("Handstand Push-up", "Press"),
    ("Strict Handstand Push-up", "Press"),
    ("Thruster", "Press"),
    ("Dumbbell Thruster", "Press"),
    # Pull
    ("Pull-up", "Pull"),
    ("Chin-up", "Pull"),
    ("Chest-to-Bar Pull-up", "Pull"),
    ("Kipping Pull-up", "Pull"),
    ("Butterfly Pull-up", "Pull"),
    ("Bar Muscle-up", "Pull"),
    ("Ring Muscle-up", "Pull"),
    ("Strict Muscle-up", "Pull"),
    ("Lat Pulldown", "Pull"),
    ("Bent Over Row", "Pull"),
    ("T-Bar Row", "Pull"),
    ("Seated Cable Row", "Pull"),
    ("Single Arm Dumbbell Row", "Pull"),
    ("Face Pull", "Pull"),
    ("Upright Row", "Pull"),
    ("Straight Arm Pulldown", "Pull"),
    ("Rope Climb", "Pull"),
    ("Legless Rope Climb", "Pull"),
    # Olympic
    ("Clean", "Olympic"),
    ("Clean and Jerk", "Olympic"),
    ("Power Clean", "Olympic"),
    ("Hang Clean", "Olympic"),
    ("Hang Power Clean", "Olympic"),
    ("Squat Clean", "Olympic"),
    ("Snatch", "Olympic"),
    ("Power Snatch", "Olympic"),
    ("Hang Snatch", "Olympic"),
    ("Hang Power Snatch", "Olympic"),
    ("Squat Snatch", "Olympic"),
    ("Muscle Snatch", "Olympic"),
    ("Snatch Balance", "Olympic"),
    ("Clean Pull", "Olympic"),
    ("Snatch Pull", "Olympic"),
    ("Push Jerk", "Olympic"),
    ("Split Jerk", "Olympic"),
    ("Jerk", "Olympic"),
    # Arms
    ("Barbell Curl", "Arms"),
    ("Bicep Curl", "Arms"),
    ("Hammer Curl", "Arms"),
    ("Concentration Curl", "Arms"),
    ("Incline Dumbbell Curl", "Arms"),
    ("Cable Curl", "Arms"),
    ("Preacher Curl", "Arms"),
    ("Zottman Curl", "Arms"),
    ("Tricep Pushdown", "Arms"),
    ("Skull Crusher", "Arms"),
    ("Tricep Dip", "Arms"),
    ("Rope Pushdown", "Arms"),
    ("Kickback", "Arms"),
    # Shoulders
    ("Lateral Raise", "Shoulders"),
    ("Cable Lateral Raise", "Shoulders"),
    ("Front Raise", "Shoulders"),
    ("Rear Delt Fly", "Shoulders"),
    # Chest
    ("Pec Deck", "Chest"),
    ("Cable Flye", "Chest"),
    ("Dumbbell Flye", "Chest"),
    ("Chest Dip", "Chest"),
    ("Bar Dip", "Chest"),
    ("Ring Dip", "Chest"),
    # Glutes / Hips
    ("Hip Thrust", "Glutes"),
    ("Glute Bridge", "Glutes"),
    ("Kettlebell Swing", "Glutes"),
    ("Russian Kettlebell Swing", "Glutes"),
    ("American Kettlebell Swing", "Glutes"),
    ("Kettlebell Turkish Get-up", "Glutes"),
    ("Kettlebell Clean", "Glutes"),
    ("Kettlebell Snatch", "Glutes"),
    # Legs
    ("Leg Curl", "Legs"),
    ("Leg Extension", "Legs"),
    ("Calf Raise", "Legs"),
    ("Seated Calf Raise", "Legs"),
    # Carry / Strongman
    ("Farmer's Carry", "Carry"),
    ("Sled Push", "Carry"),
    ("Sled Pull", "Carry"),
    ("Atlas Stone Lift", "Carry"),
    ("Tire Flip", "Carry"),
    ("Sandbag Carry", "Carry"),
    ("Sandbag Clean", "Carry"),
    ("Yoke Walk", "Carry"),
    # Core
    ("Plank", "Core"),
    ("Side Plank", "Core"),
    ("Ab Wheel Rollout", "Core"),
    ("Hollow Hold", "Core"),
    ("Dead Bug", "Core"),
    ("Bird Dog", "Core"),
    ("Crunch", "Core"),
    ("Sit-up", "Core"),
    ("V-up", "Core"),
    ("GHD Sit-up", "Core"),
    ("Knees-to-Elbow", "Core"),
    ("Toes-to-Bar", "Core"),
    ("Pallof Press", "Core"),
    ("Russian Twist", "Core"),
    ("Leg Raise", "Core"),
]


def _seed_exercise_library():
    from backend.models.exercise_library import ExerciseLibrary
    if ExerciseLibrary.query.first():
        return
    for name, category in _LIBRARY:
        db.session.add(ExerciseLibrary(name=name, category=category))
    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=8080)
