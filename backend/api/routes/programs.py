from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import program_service, program_run_service

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
    from backend.models.workout import Workout
    user_id = int(get_jwt_identity())
    program = program_service.get_program(program_id, user_id)
    if not program:
        return jsonify({"error": "Not found"}), 404

    # Find active run for this specific program
    from backend.models.program import ProgramRun
    active_run = ProgramRun.query.filter_by(
        program_id=program.id, user_id=user_id, status="active"
    ).first()

    result = program.to_dict(include_days=True, active_run=active_run)

    # Annotate days with scheduled date + workout status when run is active
    if active_run:
        workouts_by_day = program_run_service.get_run_workouts(active_run.id, user_id)
        for day in result["days"]:
            w = workouts_by_day.get(day["id"])
            if w:
                day["scheduled_date"] = w.date.date().isoformat()
                day["workout_id"] = w.id
                day["workout_status"] = w.status
            else:
                day["scheduled_date"] = None
                day["workout_id"] = None
                day["workout_status"] = None

    return jsonify(result)


@programs_bp.put("/<int:program_id>")
@jwt_required()
def update_program(program_id):
    user_id = int(get_jwt_identity())
    program = program_service.get_program(program_id, user_id)
    if not program:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json()
    program, error = program_service.update_program(program, data)
    if error:
        return jsonify({"error": error}), 409
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


