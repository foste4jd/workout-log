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
