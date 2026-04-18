from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.db.database import db
from backend.models.exercise import Exercise
from backend.models.workout import Workout
from backend.services import exercise_service, workout_service

exercises_bp = Blueprint("exercises", __name__)


@exercises_bp.get("/api/workouts/<int:workout_id>/exercises")
@jwt_required()
def list_exercises(workout_id):
    user_id = int(get_jwt_identity())
    if not workout_service.get_workout(workout_id, user_id):
        return jsonify({"error": "Workout not found"}), 404
    exercises = exercise_service.get_exercises(workout_id)
    return jsonify([e.to_dict() for e in exercises])


@exercises_bp.post("/api/workouts/<int:workout_id>/exercises")
@jwt_required()
def create_exercise(workout_id):
    user_id = int(get_jwt_identity())
    if not workout_service.get_workout(workout_id, user_id):
        return jsonify({"error": "Workout not found"}), 404
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    exercise = exercise_service.create_exercise(workout_id, data)
    return jsonify(exercise.to_dict()), 201


@exercises_bp.put("/api/exercises/<int:exercise_id>")
@jwt_required()
def update_exercise(exercise_id):
    user_id = int(get_jwt_identity())
    exercise = exercise_service.get_exercise(exercise_id)
    if not exercise:
        return jsonify({"error": "Exercise not found"}), 404
    if not workout_service.get_workout(exercise.workout_id, user_id):
        return jsonify({"error": "Not found"}), 404
    data = request.get_json()
    exercise = exercise_service.update_exercise(exercise, data)
    return jsonify(exercise.to_dict())


@exercises_bp.delete("/api/exercises/<int:exercise_id>")
@jwt_required()
def delete_exercise(exercise_id):
    user_id = int(get_jwt_identity())
    exercise = exercise_service.get_exercise(exercise_id)
    if not exercise:
        return jsonify({"error": "Exercise not found"}), 404
    if not workout_service.get_workout(exercise.workout_id, user_id):
        return jsonify({"error": "Not found"}), 404
    exercise_service.delete_exercise(exercise)
    return jsonify({"message": "Exercise deleted"})


@exercises_bp.get("/api/exercises/history")
@jwt_required()
def exercise_history():
    """All completed sets for an exercise grouped by workout session."""
    user_id = int(get_jwt_identity())
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    rows = (
        db.session.query(Exercise, Workout)
        .join(Workout, Exercise.workout_id == Workout.id)
        .filter(
            Workout.user_id == user_id,
            Workout.status == "completed",
            Exercise.name.ilike(name),
        )
        .order_by(Workout.date.desc())
        .limit(60)
        .all()
    )

    sessions = [
        {
            "date": w.date.isoformat(),
            "workout_id": w.id,
            "workout_title": w.title,
            "sets": [s.to_dict() for s in ex.set_records if s.weight_lb or s.reps],
        }
        for ex, w in rows
    ]

    return jsonify({"exercise": name, "sessions": sessions})


@exercises_bp.get("/api/exercises/last-session")
@jwt_required()
def last_session_data():
    """Return the most recent completed sets for an exercise by name."""
    user_id = int(get_jwt_identity())
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    ex = (
        Exercise.query
        .join(Workout, Exercise.workout_id == Workout.id)
        .filter(
            Workout.user_id == user_id,
            Workout.status == "completed",
            Exercise.name.ilike(name),
        )
        .order_by(Workout.date.desc())
        .first()
    )
    if not ex:
        return jsonify(None)

    w = workout_service.get_workout(ex.workout_id, user_id)
    return jsonify({
        "date": w.date.isoformat() if w else None,
        "sets": [s.to_dict() for s in ex.set_records if s.weight_lb or s.reps],
    })


@exercises_bp.patch("/api/session-sets/<int:set_id>")
@jwt_required()
def patch_set(set_id):
    """Update individual fields on a single set — used during gym execution."""
    user_id = int(get_jwt_identity())
    set_record = exercise_service.get_set(set_id)
    if not set_record:
        return jsonify({"error": "Set not found"}), 404
    # Verify ownership via exercise → workout → user
    exercise = exercise_service.get_exercise(set_record.exercise_id)
    workout = workout_service.get_workout(exercise.workout_id, user_id)
    if not workout:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    updated = exercise_service.update_set(set_record, data)
    return jsonify(updated.to_dict())
