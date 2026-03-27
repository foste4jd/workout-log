from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import workout_service, template_service

workouts_bp = Blueprint("workouts", __name__, url_prefix="/api/workouts")


@workouts_bp.get("/")
@jwt_required()
def list_workouts():
    user_id = int(get_jwt_identity())
    workouts = workout_service.get_workouts(user_id)
    return jsonify([w.to_dict() for w in workouts])


@workouts_bp.post("/")
@jwt_required()
def create_workout():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get("title"):
        return jsonify({"error": "title is required"}), 400
    workout = workout_service.create_workout(user_id, data)
    return jsonify(workout.to_dict()), 201


@workouts_bp.get("/<int:workout_id>")
@jwt_required()
def get_workout(workout_id):
    user_id = int(get_jwt_identity())
    workout = workout_service.get_workout(workout_id, user_id)
    if not workout:
        return jsonify({"error": "Workout not found"}), 404
    return jsonify(workout.to_dict())


@workouts_bp.put("/<int:workout_id>")
@jwt_required()
def update_workout(workout_id):
    user_id = int(get_jwt_identity())
    workout = workout_service.get_workout(workout_id, user_id)
    if not workout:
        return jsonify({"error": "Workout not found"}), 404
    data = request.get_json()
    workout = workout_service.update_workout(workout, data)
    return jsonify(workout.to_dict())


@workouts_bp.post("/<int:workout_id>/complete")
@jwt_required()
def complete_workout(workout_id):
    user_id = int(get_jwt_identity())
    workout = workout_service.get_workout(workout_id, user_id)
    if not workout:
        return jsonify({"error": "Workout not found"}), 404
    data = request.get_json() or {}
    workout = workout_service.complete_workout(workout, data.get("duration_minutes"))
    return jsonify(workout.to_dict())


@workouts_bp.post("/<int:workout_id>/copy")
@jwt_required()
def copy_workout(workout_id):
    """Copy a prior session into a new planned session."""
    user_id = int(get_jwt_identity())
    source = workout_service.get_workout(workout_id, user_id)
    if not source:
        return jsonify({"error": "Workout not found"}), 404
    data = request.get_json() or {}
    new_session = template_service.copy_session(source, user_id, data.get("date"))
    return jsonify(new_session.to_dict()), 201


@workouts_bp.post("/<int:workout_id>/save-as-template")
@jwt_required()
def save_as_template(workout_id):
    user_id = int(get_jwt_identity())
    workout = workout_service.get_workout(workout_id, user_id)
    if not workout:
        return jsonify({"error": "Workout not found"}), 404
    data = request.get_json() or {}
    name = data.get("name") or workout.title
    template = template_service.create_template_from_workout(
        user_id, workout, name, data.get("description")
    )
    return jsonify(template.to_dict(include_exercises=True)), 201


@workouts_bp.delete("/<int:workout_id>")
@jwt_required()
def delete_workout(workout_id):
    user_id = int(get_jwt_identity())
    workout = workout_service.get_workout(workout_id, user_id)
    if not workout:
        return jsonify({"error": "Workout not found"}), 404
    workout_service.delete_workout(workout)
    return jsonify({"message": "Workout deleted"}), 200
