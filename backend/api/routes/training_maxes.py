from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import training_max_service
from backend.models.exercise_library import ExerciseLibrary

training_maxes_bp = Blueprint("training_maxes", __name__, url_prefix="/api/training-maxes")


@training_maxes_bp.get("/")
@jwt_required()
def list_maxes():
    user_id = int(get_jwt_identity())
    return jsonify([m.to_dict() for m in training_max_service.get_training_maxes(user_id)])


@training_maxes_bp.post("/")
@jwt_required()
def upsert_max():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get("exercise_id") or not data.get("training_max_weight"):
        return jsonify({"error": "exercise_id and training_max_weight are required"}), 400

    exercise = ExerciseLibrary.query.get(data["exercise_id"])
    if not exercise:
        return jsonify({"error": "Exercise not found"}), 404

    record = training_max_service.upsert_training_max(
        user_id=user_id,
        exercise_id=data["exercise_id"],
        weight=float(data["training_max_weight"]),
        notes=data.get("notes"),
    )
    return jsonify(record.to_dict()), 200


@training_maxes_bp.delete("/<int:max_id>")
@jwt_required()
def delete_max(max_id):
    user_id = int(get_jwt_identity())
    from backend.models.training_max import TrainingMax
    record = TrainingMax.query.filter_by(id=max_id, user_id=user_id).first()
    if not record:
        return jsonify({"error": "Not found"}), 404
    training_max_service.delete_training_max(record)
    return jsonify({"message": "Deleted"}), 200
