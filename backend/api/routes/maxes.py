from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import max_service
from backend.models.personal_max import PersonalMax

maxes_bp = Blueprint("maxes", __name__, url_prefix="/api/maxes")


@maxes_bp.get("/")
@jwt_required()
def list_maxes():
    user_id = int(get_jwt_identity())
    return jsonify([m.to_dict() for m in max_service.get_maxes(user_id)])


@maxes_bp.post("/")
@jwt_required()
def upsert_max():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get("exercise_name") or not data.get("weight_lb"):
        return jsonify({"error": "exercise_name and weight_lb are required"}), 400
    record = max_service.upsert_max(user_id, data["exercise_name"], float(data["weight_lb"]))
    return jsonify(record.to_dict()), 200


@maxes_bp.delete("/<int:max_id>")
@jwt_required()
def delete_max(max_id):
    user_id = int(get_jwt_identity())
    record = PersonalMax.query.filter_by(id=max_id, user_id=user_id).first()
    if not record:
        return jsonify({"error": "Not found"}), 404
    max_service.delete_max(record)
    return jsonify({"message": "Deleted"}), 200