from backend.db.database import db
from backend.models.exercise import Exercise
from backend.models.exercise_set import ExerciseSet


def get_exercises(workout_id):
    return Exercise.query.filter_by(workout_id=workout_id).all()


def get_exercise(exercise_id):
    return Exercise.query.get(exercise_id)


def create_exercise(workout_id, data):
    exercise = Exercise(
        workout_id=workout_id,
        exercise_library_id=data.get("exercise_library_id"),
        name=data["name"],
        notes=data.get("notes"),
    )
    db.session.add(exercise)
    db.session.flush()

    for i, s in enumerate(data.get("sets", []), 1):
        db.session.add(ExerciseSet(
            exercise_id=exercise.id,
            set_number=i,
            set_type=s.get("set_type", "working"),
            reps=s.get("reps"),
            weight_lb=s.get("weight_lb"),
            percent=s.get("percent"),
            duration_seconds=s.get("duration_seconds"),
            completed=s.get("completed", True),
        ))

    db.session.commit()
    return exercise


def update_exercise(exercise, data):
    exercise.name = data.get("name", exercise.name)
    exercise.notes = data.get("notes", exercise.notes)
    if "exercise_library_id" in data:
        exercise.exercise_library_id = data["exercise_library_id"]

    if "sets" in data:
        for s in list(exercise.set_records):
            db.session.delete(s)
        db.session.flush()
        for i, s in enumerate(data["sets"], 1):
            db.session.add(ExerciseSet(
                exercise_id=exercise.id,
                set_number=i,
                set_type=s.get("set_type", "working"),
                reps=s.get("reps"),
                weight_lb=s.get("weight_lb"),
                percent=s.get("percent"),
                duration_seconds=s.get("duration_seconds"),
                completed=s.get("completed", True),
            ))

    db.session.commit()
    return exercise


def update_set(set_record, data):
    """Patch individual fields on a single set — used during gym execution."""
    if "reps" in data:
        set_record.reps = data["reps"]
    if "weight_lb" in data:
        set_record.weight_lb = data["weight_lb"]
    if "percent" in data:
        set_record.percent = data["percent"]
    if "duration_seconds" in data:
        set_record.duration_seconds = data["duration_seconds"]
    if "completed" in data:
        set_record.completed = data["completed"]
    if "set_type" in data:
        set_record.set_type = data["set_type"]
    db.session.commit()
    return set_record


def get_set(set_id):
    return ExerciseSet.query.get(set_id)


def delete_exercise(exercise):
    db.session.delete(exercise)
    db.session.commit()
