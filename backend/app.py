import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from backend.config import Config
from backend.db.database import db

bcrypt = Bcrypt()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=[], storage_uri="memory://")
migrate = Migrate()

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
    limiter.init_app(app)
    migrate.init_app(app, db)

    # ── Import all models so SQLAlchemy registers them ────────────────────────
    from backend.models.user import User  # noqa: F401
    from backend.models.workout import Workout  # noqa: F401
    from backend.models.exercise import Exercise  # noqa: F401
    from backend.models.exercise_set import ExerciseSet  # noqa: F401
    from backend.models.exercise_library import ExerciseLibrary  # noqa: F401
    from backend.models.training_max import TrainingMax  # noqa: F401
    from backend.models.workout_template import (  # noqa: F401
        WorkoutTemplate, WorkoutTemplateExercise, WorkoutTemplateSet
    )
    from backend.models.ai_knowledge import AIKnowledge  # noqa: F401
    from backend.models.program import Program, ProgramDay  # noqa: F401
    from backend.models.user_profile import UserProfile  # noqa: F401
    from backend.models.bodyweight_entry import BodyweightEntry  # noqa: F401

    # ── Register blueprints ───────────────────────────────────────────────────
    from backend.api.routes.users import users_bp
    from backend.api.routes.workouts import workouts_bp
    from backend.api.routes.exercises import exercises_bp
    from backend.api.routes.views import views_bp
    from backend.api.routes.stats import stats_bp
    from backend.api.routes.library import library_bp
    from backend.api.routes.training_maxes import training_maxes_bp
    from backend.api.routes.templates import templates_bp
    from backend.api.routes.ai_trainer import ai_trainer_bp
    from backend.api.routes.programs import programs_bp
    from backend.api.routes.profile import profile_bp

    for bp in (
        users_bp, workouts_bp, exercises_bp, views_bp, stats_bp,
        library_bp, training_maxes_bp, templates_bp,
        ai_trainer_bp, programs_bp, profile_bp,
    ):
        app.register_blueprint(bp)

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    with app.app_context():
        db.create_all()
        _seed_exercise_library()

    return app



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
