from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.workout import Workout
from backend.models.exercise import Exercise

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/api/stats")
@jwt_required()
def get_stats():
    user_id = int(get_jwt_identity())

    workouts = Workout.query.filter_by(user_id=user_id).all()
    exercises = (
        Exercise.query
        .join(Workout)
        .filter(Workout.user_id == user_id)
        .all()
    )

    now = datetime.now(timezone.utc)
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    total_workouts = len(workouts)
    total_minutes = sum(w.duration_minutes or 0 for w in workouts)
    this_week = sum(1 for w in workouts if w.date.date() >= monday)
    this_month = sum(1 for w in workouts if w.date.date() >= month_start)

    # Current streak (count consecutive days with workouts ending today or yesterday)
    workout_dates = set(w.date.date() for w in workouts)
    streak = 0
    check = today
    if check not in workout_dates:
        check = today - timedelta(days=1)
    while check in workout_dates:
        streak += 1
        check -= timedelta(days=1)

    # Personal records — max weight per exercise across all sets
    pr_map = {}
    for e in exercises:
        for s in e.set_records:
            if s.weight_lb:
                key = e.name.lower()
                if key not in pr_map or s.weight_lb > pr_map[key]["weight_lb"]:
                    pr_map[key] = {
                        "name": e.name,
                        "weight_lb": s.weight_lb,
                        "reps": s.reps,
                        "sets": len(e.set_records),
                    }
    personal_records = sorted(
        pr_map.values(), key=lambda x: x["weight_lb"], reverse=True
    )[:10]

    # Top exercises by frequency
    ex_counter = Counter(e.name for e in exercises)
    top_exercises = [
        {"name": n, "count": c} for n, c in ex_counter.most_common(8)
    ]

    # Daily activity for last 84 days (12 weeks)
    activity_map = defaultdict(int)
    for w in workouts:
        activity_map[w.date.date().isoformat()] += 1

    daily_activity = []
    for i in range(83, -1, -1):
        d = today - timedelta(days=i)
        daily_activity.append({
            "date": d.isoformat(),
            "count": activity_map.get(d.isoformat(), 0),
        })

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
