from datetime import datetime, timezone, timedelta, time as dt_time
from zoneinfo import ZoneInfo
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from backend.db.database import db
from backend.models.user import User
from backend.models.workout import Workout
from backend.models.exercise import Exercise
from backend.models.exercise_set import ExerciseSet

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/api/stats")
@jwt_required()
def get_stats():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    tz = ZoneInfo(user.timezone or "UTC")

    now = datetime.now(tz)
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    window_start = today - timedelta(days=83)

    # Naive datetimes matching how SQLite stores dates in this app
    monday_dt = datetime.combine(monday, dt_time.min)
    month_dt = datetime.combine(month_start, dt_time.min)
    window_dt = datetime.combine(window_start, dt_time.min)

    # Scalar aggregates via SQL
    total_workouts = (
        db.session.query(func.count(Workout.id))
        .filter_by(user_id=user_id).scalar() or 0
    )
    total_minutes = (
        db.session.query(func.sum(Workout.duration_minutes))
        .filter_by(user_id=user_id).scalar() or 0
    )
    this_week = (
        db.session.query(func.count(Workout.id))
        .filter(Workout.user_id == user_id, Workout.date >= monday_dt)
        .scalar() or 0
    )
    this_month = (
        db.session.query(func.count(Workout.id))
        .filter(Workout.user_id == user_id, Workout.date >= month_dt)
        .scalar() or 0
    )

    # Current streak — lightweight date-only query
    date_rows = (
        db.session.query(func.date(Workout.date))
        .filter_by(user_id=user_id).distinct().all()
    )
    # SQLite returns strings; Postgres returns date objects — normalise to str
    workout_dates = {str(r[0]) for r in date_rows}
    streak = 0
    check = today
    if str(check) not in workout_dates:
        check = today - timedelta(days=1)
    while str(check) in workout_dates:
        streak += 1
        check -= timedelta(days=1)

    # Personal records — max weight per exercise via SQL
    pr_rows = (
        db.session.query(
            Exercise.name,
            func.max(ExerciseSet.weight_lb).label("max_weight"),
            func.count(ExerciseSet.id).label("set_count"),
        )
        .join(Exercise, ExerciseSet.exercise_id == Exercise.id)
        .join(Workout, Exercise.workout_id == Workout.id)
        .filter(Workout.user_id == user_id, ExerciseSet.weight_lb.isnot(None), ExerciseSet.completed == True)
        .group_by(func.lower(Exercise.name))
        .order_by(func.max(ExerciseSet.weight_lb).desc())
        .limit(10)
        .all()
    )
    personal_records = [
        {"name": r.name, "weight_lb": r.max_weight, "sets": r.set_count}
        for r in pr_rows
    ]

    # Top exercises by frequency via SQL
    top_rows = (
        db.session.query(Exercise.name, func.count(Exercise.id).label("cnt"))
        .join(Workout, Exercise.workout_id == Workout.id)
        .filter(Workout.user_id == user_id)
        .group_by(func.lower(Exercise.name))
        .order_by(func.count(Exercise.id).desc())
        .limit(8)
        .all()
    )
    top_exercises = [{"name": r.name, "count": r.cnt} for r in top_rows]

    # Daily activity — last 84 days via SQL, gaps filled in Python
    activity_rows = (
        db.session.query(
            func.date(Workout.date).label("d"),
            func.count(Workout.id).label("cnt"),
        )
        .filter(Workout.user_id == user_id, Workout.date >= window_dt)
        .group_by(func.date(Workout.date))
        .all()
    )
    activity_map = {str(r.d): r.cnt for r in activity_rows}
    daily_activity = [
        {
            "date": (today - timedelta(days=i)).isoformat(),
            "count": activity_map.get((today - timedelta(days=i)).isoformat(), 0),
        }
        for i in range(83, -1, -1)
    ]

    return jsonify({
        "total_workouts": total_workouts,
        "total_minutes": total_minutes,
        "this_week": this_week,
        "this_month": this_month,
        "current_streak": streak,
        "personal_records": personal_records,
        "top_exercises": top_exercises,
        "daily_activity": daily_activity,
    })
