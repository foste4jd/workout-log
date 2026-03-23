from backend.db.database import db
from backend.models.workout import Workout


def get_workouts(user_id):
    return Workout.query.filter_by(user_id=user_id).order_by(Workout.date.desc()).all()


def get_workout(workout_id, user_id):
    return Workout.query.filter_by(id=workout_id, user_id=user_id).first()


def create_workout(user_id, data):
    workout = Workout(
        user_id=user_id,
        title=data["title"],
        notes=data.get("notes"),
        duration_minutes=data.get("duration_minutes"),
    )
    db.session.add(workout)
    db.session.commit()
    return workout


def update_workout(workout, data):
    workout.title = data.get("title", workout.title)
    workout.notes = data.get("notes", workout.notes)
    workout.duration_minutes = data.get("duration_minutes", workout.duration_minutes)
    db.session.commit()
    return workout


def delete_workout(workout):
    db.session.delete(workout)
    db.session.commit()
