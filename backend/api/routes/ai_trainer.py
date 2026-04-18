from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.services import ai_trainer_service, interpret_service
from backend.models.ai_knowledge import AIKnowledge
from backend.models.exercise_library import ExerciseLibrary
from backend.models.training_max import TrainingMax
from backend.db.database import db

ai_trainer_bp = Blueprint("ai_trainer", __name__, url_prefix="/api/ai")


@ai_trainer_bp.post("/interpret")
@jwt_required()
def interpret_workout():
    """Parse free-form natural-language text into a canonical multi-exercise workout payload."""
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}
    text    = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    library          = ExerciseLibrary.query.filter_by(is_active=True).all()
    library_exercises = [{"id": e.id, "name": e.name} for e in library]

    tms = TrainingMax.query.filter_by(user_id=user_id).all()
    training_maxes = {
        tm.exercise.name: tm.training_max_weight
        for tm in tms if tm.exercise
    }

    result = interpret_service.interpret_workout(text, library_exercises, training_maxes)
    return jsonify(result)


@ai_trainer_bp.post("/title")
@jwt_required()
def generate_title():
    """Generate a short workout title from exercise names. Cheap: ~10 output tokens."""
    data      = request.get_json() or {}
    exercises = [str(e)[:60] for e in (data.get("exercises") or [])[:8] if str(e).strip()]
    weekday   = (data.get("weekday") or "").strip()[:20]
    if not exercises:
        return jsonify({"title": ""}), 200
    title = ai_trainer_service.generate_title(exercises, weekday)
    return jsonify({"title": title})


@ai_trainer_bp.post("/suggest")
@jwt_required()
def suggest():
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}
    prompt  = (data.get("prompt") or "").strip()
    # allow_web intentionally ignored — web search disabled for workout generation

    result = ai_trainer_service.handle_suggest(user_id, prompt)
    return jsonify(result)


@ai_trainer_bp.post("/accept")
@jwt_required()
def accept():
    """Convert an AI-generated workout result into a real workout record."""
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}

    ai_result = data.get("ai_result")
    date_str  = data.get("date")          # optional YYYY-MM-DD
    if not ai_result:
        return jsonify({"error": "ai_result is required"}), 400

    workout = ai_trainer_service.accept_workout(user_id, ai_result, date_str)
    return jsonify(workout), 201


@ai_trainer_bp.post("/save-template")
@jwt_required()
def save_template():
    """Save an AI-generated workout directly as a named template."""
    user_id = int(get_jwt_identity())
    data    = request.get_json() or {}
    ai_result = data.get("ai_result")
    if not ai_result:
        return jsonify({"error": "ai_result is required"}), 400

    template = ai_trainer_service.save_as_template(user_id, ai_result)
    return jsonify(template), 201


# ── Memory admin ───────────────────────────────────────────────────────────────

@ai_trainer_bp.get("/memory")
@jwt_required()
def list_memory():
    user_id = int(get_jwt_identity())
    entries = (
        AIKnowledge.query
        .filter_by(user_id=user_id)
        .order_by(AIKnowledge.updated_at.desc())
        .all()
    )
    return jsonify([e.to_dict() for e in entries])


@ai_trainer_bp.delete("/memory/<int:memory_id>")
@jwt_required()
def delete_memory(memory_id):
    user_id = int(get_jwt_identity())
    entry = AIKnowledge.query.filter_by(id=memory_id, user_id=user_id).first()
    if not entry:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@ai_trainer_bp.patch("/memory/<int:memory_id>")
@jwt_required()
def toggle_memory(memory_id):
    """Activate or deactivate a memory without deleting it."""
    user_id = int(get_jwt_identity())
    entry = AIKnowledge.query.filter_by(id=memory_id, user_id=user_id).first()
    if not entry:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    if "is_active" in data:
        entry.is_active = bool(data["is_active"])
    db.session.commit()
    return jsonify(entry.to_dict())
