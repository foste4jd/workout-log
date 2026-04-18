from datetime import date
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models.user import User
from backend.services import profile_service

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.get("")
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    unit = user.unit or "lb"
    profile = profile_service.get_or_create_profile(user_id)
    latest_bw = profile_service.get_latest_bodyweight(user_id)
    recent_bw = profile_service.get_bodyweight_history(user_id, limit=5)
    return jsonify({
        "profile": profile.to_dict(),
        "latest_bodyweight": latest_bw.to_dict(unit) if latest_bw else None,
        "recent_bodyweight": [e.to_dict(unit) for e in recent_bw],
        "unit": unit,
        "username": user.username,
    })


@profile_bp.put("")
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    profile, errors = profile_service.update_profile(user_id, data)
    if errors:
        return jsonify({"error": errors[0]}), 400
    return jsonify({"profile": profile.to_dict()})


@profile_bp.post("/bodyweight")
@jwt_required()
def log_bodyweight():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    unit = user.unit or "lb"
    data = request.get_json() or {}

    weight_raw = data.get("weight")
    if weight_raw is None:
        return jsonify({"error": "weight is required"}), 400
    try:
        weight_input = float(weight_raw)
        if weight_input <= 0 or weight_input > 999:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid weight value"}), 400

    weight_kg = weight_input if unit == "kg" else weight_input / 2.20462

    date_str = data.get("date")
    try:
        recorded_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    entry = profile_service.add_bodyweight_entry(
        user_id, weight_kg, recorded_date, data.get("notes")
    )
    return jsonify({"entry": entry.to_dict(unit)}), 201


@profile_bp.get("/bodyweight")
@jwt_required()
def get_bodyweight():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    unit = user.unit or "lb"
    limit = min(int(request.args.get("limit", 30)), 90)
    entries = profile_service.get_bodyweight_history(user_id, limit=limit)
    return jsonify({"entries": [e.to_dict(unit) for e in entries], "unit": unit})
