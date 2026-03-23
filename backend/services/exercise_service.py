from backend.db.database import db
from backend.models.exercise import Exercise


def get_exercises(workout_id):
    return Exercise.query.filter_by(workout_id=workout_id).all()


def get_exercise(exercise_id):
    return Exercise.query.get(exercise_id)


def create_exercise(workout_id, data):
    exercise = Exercise(
        workout_id=workout_id,
        name=data["name"],
        sets=data.get("sets"),
        reps=data.get("reps"),
        weight_kg=data.get("weight_kg"),
        notes=data.get("notes"),
    )
    db.session.add(exercise)
    db.session.commit()
    return exercise


def update_exercise(exercise, data):
    exercise.name = data.get("name", exercise.name)
    exercise.sets = data.get("sets", exercise.sets)
    exercise.reps = data.get("reps", exercise.reps)
    exercise.weight_kg = data.get("weight_kg", exercise.weight_kg)
    exercise.notes = data.get("notes", exercise.notes)
    db.session.commit()
    return exercise


def delete_exercise(exercise):
    db.session.delete(exercise)
    db.session.commit()
