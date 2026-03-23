from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import workout_service

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


@workouts_bp.delete("/<int:workout_id>")
@jwt_required()
def delete_workout(workout_id):
    user_id = int(get_jwt_identity())
    workout = workout_service.get_workout(workout_id, user_id)
    if not workout:
        return jsonify({"error": "Workout not found"}), 404
    workout_service.delete_workout(workout)
    return jsonify({"message": "Workout deleted"}), 200
