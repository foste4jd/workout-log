from flask import Blueprint, render_template, redirect, url_for
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from backend import ai_config
from backend.models.user import User

views_bp = Blueprint("views", __name__)


def _get_username():
    """Verify cookie JWT and return username, or None if unauthenticated."""
    try:
        verify_jwt_in_request(locations=["cookies"])
        user = User.query.get(int(get_jwt_identity()))
        return user.username if user else None
    except Exception:
        return None


def _get_user():
    """Verify cookie JWT and return User object, or None if unauthenticated."""
    try:
        verify_jwt_in_request(locations=["cookies"])
        return User.query.get(int(get_jwt_identity()))
    except Exception:
        return None


@views_bp.get("/")
def index():
    if _get_username():
        return redirect(url_for("views.dashboard"))
    return redirect(url_for("views.login"))


@views_bp.get("/login")
def login():
    if _get_username():
        return redirect(url_for("views.workouts"))
    return render_template("login.html")


@views_bp.get("/workouts")
def workouts():
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("workouts.html", username=username)


@views_bp.get("/dashboard")
def dashboard():
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("dashboard.html", username=username)


@views_bp.get("/log")
def log_workout():
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("log.html", ui_max_regens=ai_config.UI_MAX_REGENS, username=username)


@views_bp.get("/maxes")
def maxes_page():
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("maxes.html", username=username)


@views_bp.get("/templates")
def templates_page():
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("templates.html", username=username)


@views_bp.get("/session/<int:workout_id>")
def session_page(workout_id):
    user = _get_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("session.html", workout_id=workout_id, unit=user.unit or "lb")


@views_bp.get("/ai-memory")
def ai_memory_page():
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("ai_memory.html", username=username)


@views_bp.get("/exercise-history")
def exercise_history_page():
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("exercise_history.html", username=username)


@views_bp.get("/programs")
def programs_page():
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("programs.html", username=username)


@views_bp.get("/programs/<int:program_id>")
def program_detail_page(program_id):
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("program_detail.html", username=username, program_id=program_id)


@views_bp.get("/account")
def account_page():
    username = _get_username()
    if not username:
        return redirect(url_for("views.login"))
    return render_template("account.html", username=username)
