from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import program_run_service
from backend.models.workout import Workout

program_runs_bp = Blueprint("program_runs", __name__)


@program_runs_bp.post("/api/programs/<int:program_id>/runs")
@jwt_required()
def start_program(program_id):
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    run, error = program_run_service.start_program(
        program_id, user_id,
        data.get("start_date"),
        data.get("training_days", []),
    )
    if error:
        return jsonify({"error": error}), 400
    return jsonify(run.to_dict(include_program=True)), 201


@program_runs_bp.delete("/api/program-runs/<int:run_id>")
@jwt_required()
def cancel_run(run_id):
    user_id = int(get_jwt_identity())
    run, error = program_run_service.cancel_run(run_id, user_id)
    if error:
        return jsonify({"error": error}), 404
    return jsonify({"message": "Run cancelled", "run": run.to_dict()}), 200


@program_runs_bp.patch("/api/program-runs/<int:run_id>/complete")
@jwt_required()
def complete_run(run_id):
    user_id = int(get_jwt_identity())
    run, error = program_run_service.complete_run(run_id, user_id)
    if error:
        return jsonify({"error": error}), 404
    return jsonify(run.to_dict()), 200


@program_runs_bp.get("/api/program-runs/active")
@jwt_required()
def get_active_run():
    user_id = int(get_jwt_identity())
    run = program_run_service.get_active_run(user_id)
    if not run:
        return jsonify(None), 200

    result = run.to_dict(include_program=True)

    # Compute current week number
    today = date.today()
    days_elapsed = max(0, (today - run.start_date).days)
    current_week = min(days_elapsed // 7 + 1, run.program.total_weeks)
    result["current_week"] = current_week

    # Find today's planned workout (if any)
    today_workout = (
        Workout.query
        .filter_by(user_id=user_id, program_run_id=run.id, status="planned")
        .filter(Workout.date >= _day_start(today), Workout.date < _day_start(today + timedelta(days=1)))
        .first()
    )
    if today_workout:
        result["today_workout"] = today_workout.to_dict()
    else:
        result["today_workout"] = None

    return jsonify(result), 200


@program_runs_bp.post("/api/programs/<int:program_id>/duplicate")
@jwt_required()
def duplicate_program(program_id):
    user_id = int(get_jwt_identity())
    program = program_run_service.duplicate_program(program_id, user_id)
    if not program:
        return jsonify({"error": "Not found"}), 404
    return jsonify(program.to_dict(include_days=True)), 201


def _day_start(d):
    from datetime import datetime, timezone
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
