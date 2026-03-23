from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
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
    exercise = exercise_service.get_exercise(exercise_id)
    if not exercise:
        return jsonify({"error": "Exercise not found"}), 404
    data = request.get_json()
    exercise = exercise_service.update_exercise(exercise, data)
    return jsonify(exercise.to_dict())


@exercises_bp.delete("/api/exercises/<int:exercise_id>")
@jwt_required()
def delete_exercise(exercise_id):
    exercise = exercise_service.get_exercise(exercise_id)
    if not exercise:
        return jsonify({"error": "Exercise not found"}), 404
    exercise_service.delete_exercise(exercise)
    return jsonify({"message": "Exercise deleted"})
