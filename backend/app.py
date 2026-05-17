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
    from backend.models.program import Program, ProgramDay, ProgramRun  # noqa: F401
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
    from backend.api.routes.program_runs import program_runs_bp
    from backend.api.routes.profile import profile_bp

    for bp in (
        users_bp, workouts_bp, exercises_bp, views_bp, stats_bp,
        library_bp, training_maxes_bp, templates_bp,
        ai_trainer_bp, programs_bp, program_runs_bp, profile_bp,
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

def _seed_exercise_library():
    import json
    import os
    from sqlalchemy import inspect as sa_inspect
    from backend.models.exercise_library import ExerciseLibrary

    # Skip if any required columns are absent (migration not yet applied).
    # Both aliases (v2) and tier (v3) must exist before we can seed.
    cols = {c["name"] for c in sa_inspect(db.engine).get_columns("exercise_library")}
    if "aliases" not in cols or "tier" not in cols:
        return

    # Skip if already seeded with v3 data
    sample = ExerciseLibrary.query.filter_by(is_custom=False).first()
    if sample and sample.tier is not None:
        return

    data_path = os.path.join(os.path.dirname(__file__), "data", "exercises.json")
    with open(data_path) as f:
        exercises = json.load(f)

    ExerciseLibrary.query.filter_by(is_custom=False).delete()
    for ex in exercises:
        db.session.add(ExerciseLibrary(
            name=ex["name"],
            aliases=ex.get("aliases", []),
            primary_muscle=ex.get("primary_muscle"),
            secondary_muscles=ex.get("secondary_muscles", []),
            equipment=ex.get("equipment", []),
            movement_pattern=ex.get("movement_pattern"),
            unilateral=ex.get("unilateral", False),
            sort_order=ex.get("sort_order", 500),
            is_custom=False,
            category=ex.get("category") or ex.get("movement_pattern", ""),
            tier=ex.get("tier"),
            parent=ex.get("parent"),
        ))
    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=8080)
