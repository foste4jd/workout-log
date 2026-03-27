from flask import Blueprint, render_template

views_bp = Blueprint("views", __name__)


@views_bp.get("/")
def index():
    return render_template("index.html")


@views_bp.get("/login")
def login():
    return render_template("login.html")


@views_bp.get("/workouts")
def workouts():
    return render_template("workouts.html")


@views_bp.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@views_bp.get("/log")
def log_workout():
    return render_template("log.html")


@views_bp.get("/maxes")
def maxes_page():
    return render_template("maxes.html")


@views_bp.get("/templates")
def templates_page():
    return render_template("templates.html")


@views_bp.get("/session/<int:workout_id>")
def session_page(workout_id):
    return render_template("session.html", workout_id=workout_id)
