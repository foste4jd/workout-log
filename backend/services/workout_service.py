from datetime import datetime, timezone
from backend.db.database import db
from backend.models.workout import Workout


def get_workouts(user_id):
    return Workout.query.filter_by(user_id=user_id).order_by(Workout.date.desc()).all()


def get_workouts_filtered(user_id, status=None, date_from=None, date_to=None, limit=None):
    from sqlalchemy import func
    q = Workout.query.filter_by(user_id=user_id)
    if status:
        q = q.filter(Workout.status == status)
    if date_from:
        q = q.filter(func.date(Workout.date) >= date_from)
    if date_to:
        q = q.filter(func.date(Workout.date) <= date_to)
    q = q.order_by(Workout.date.desc())
    if limit:
        q = q.limit(limit)
    return q.all()


def get_workouts_page(user_id, page, per_page=100):
    return (
        Workout.query
        .filter_by(user_id=user_id)
        .order_by(Workout.date.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )


def get_workout(workout_id, user_id):
    return Workout.query.filter_by(id=workout_id, user_id=user_id).first()


def create_workout(user_id, data):
    date = datetime.now(timezone.utc)
    if data.get("date"):
        try:
            date = datetime.fromisoformat(data["date"])
        except ValueError:
            pass

    workout = Workout(
        user_id=user_id,
        title=data["title"],
        notes=data.get("notes"),
        duration_minutes=data.get("duration_minutes"),
        date=date,
        status=data.get("status", "completed"),
    )
    db.session.add(workout)
    db.session.commit()
    return workout


def update_workout(workout, data):
    workout.title = data.get("title", workout.title)
    workout.notes = data.get("notes", workout.notes)
    workout.duration_minutes = data.get("duration_minutes", workout.duration_minutes)
    if "status" in data:
        workout.status = data["status"]
    if "date" in data and data["date"]:
        try:
            workout.date = datetime.fromisoformat(data["date"])
        except (ValueError, TypeError):
            pass
    db.session.commit()
    return workout


def complete_workout(workout, duration_minutes=None):
    workout.status = "completed"
    if duration_minutes is not None:
        workout.duration_minutes = duration_minutes
    db.session.commit()
    return workout


def delete_workout(workout):
    db.session.delete(workout)
    db.session.commit()
