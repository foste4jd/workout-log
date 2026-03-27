from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import template_service

templates_bp = Blueprint("templates", __name__, url_prefix="/api/templates")


@templates_bp.get("/")
@jwt_required()
def list_templates():
    user_id = int(get_jwt_identity())
    templates = template_service.get_templates(user_id)
    return jsonify([t.to_dict(include_exercises=True) for t in templates])


@templates_bp.post("/")
@jwt_required()
def create_template():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    template = template_service.create_template(user_id, data)
    return jsonify(template.to_dict(include_exercises=True)), 201


@templates_bp.get("/<int:template_id>")
@jwt_required()
def get_template(template_id):
    user_id = int(get_jwt_identity())
    template = template_service.get_template(template_id, user_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404
    return jsonify(template.to_dict(include_exercises=True))


@templates_bp.put("/<int:template_id>")
@jwt_required()
def update_template(template_id):
    user_id = int(get_jwt_identity())
    template = template_service.get_template(template_id, user_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404
    data = request.get_json()
    template = template_service.update_template(template, data)
    return jsonify(template.to_dict(include_exercises=True))


@templates_bp.delete("/<int:template_id>")
@jwt_required()
def delete_template(template_id):
    user_id = int(get_jwt_identity())
    template = template_service.get_template(template_id, user_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404
    template_service.delete_template(template)
    return jsonify({"message": "Deleted"}), 200


@templates_bp.post("/<int:template_id>/start")
@jwt_required()
def start_from_template(template_id):
    """Snapshot the template into a new planned WorkoutSession and return its id."""
    user_id = int(get_jwt_identity())
    template = template_service.get_template(template_id, user_id)
    if not template:
        return jsonify({"error": "Template not found"}), 404
    data = request.get_json() or {}
    session = template_service.create_session_from_template(template, user_id, data.get("date"))
    return jsonify(session.to_dict()), 201
