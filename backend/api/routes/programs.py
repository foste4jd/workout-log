from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import program_service

programs_bp = Blueprint("programs", __name__, url_prefix="/api/programs")


@programs_bp.get("/")
@jwt_required()
def list_programs():
    user_id = int(get_jwt_identity())
    programs = program_service.get_programs(user_id)
    return jsonify([p.to_dict(include_days=True) for p in programs])


@programs_bp.post("/")
@jwt_required()
def create_program():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    program = program_service.create_program(user_id, data)
    return jsonify(program.to_dict(include_days=True)), 201


@programs_bp.get("/<int:program_id>")
@jwt_required()
def get_program(program_id):
    user_id = int(get_jwt_identity())
    program = program_service.get_program(program_id, user_id)
    if not program:
        return jsonify({"error": "Not found"}), 404
    return jsonify(program.to_dict(include_days=True))


@programs_bp.put("/<int:program_id>")
@jwt_required()
def update_program(program_id):
    user_id = int(get_jwt_identity())
    program = program_service.get_program(program_id, user_id)
    if not program:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json()
    program = program_service.update_program(program, data)
    return jsonify(program.to_dict(include_days=True))


@programs_bp.delete("/<int:program_id>")
@jwt_required()
def delete_program(program_id):
    user_id = int(get_jwt_identity())
    program = program_service.get_program(program_id, user_id)
    if not program:
        return jsonify({"error": "Not found"}), 404
    program_service.delete_program(program)
    return jsonify({"message": "Deleted"}), 200


@programs_bp.post("/<int:program_id>/days/<int:day_id>/start")
@jwt_required()
def start_day(program_id, day_id):
    user_id = int(get_jwt_identity())
    program = program_service.get_program(program_id, user_id)
    if not program:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    session = program_service.start_program_day(program, day_id, user_id, data.get("date"))
    if not session:
        return jsonify({"error": "Day has no template or template not found"}), 400
    return jsonify(session.to_dict()), 201
