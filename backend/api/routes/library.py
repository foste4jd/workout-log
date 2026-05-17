from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from backend.services import library_service

library_bp = Blueprint("library", __name__, url_prefix="/api/library")


@library_bp.get("/")
@jwt_required()
def list_exercises():
    equipment = request.args.get("equipment")
    movement_pattern = request.args.get("movement_pattern")
    muscle = request.args.get("muscle")
    category = request.args.get("category")
    tier = request.args.get("tier")
    exercises = library_service.list_all(
        equipment=equipment,
        movement_pattern=movement_pattern,
        muscle=muscle,
        category=category,
        tier=tier,
    )
    return jsonify([e.to_dict() for e in exercises])


@library_bp.get("/search")
@jwt_required()
def search_exercises():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    limit = min(int(request.args.get("limit", 20)), 50)
    equipment = request.args.get("equipment")
    movement_pattern = request.args.get("movement_pattern")
    muscle = request.args.get("muscle")
    category = request.args.get("category")
    tier = request.args.get("tier")
    results = library_service.search(
        query,
        limit=limit,
        equipment=equipment,
        movement_pattern=movement_pattern,
        muscle=muscle,
        category=category,
        tier=tier,
    )
    return jsonify([e.to_dict() for e in results])


@library_bp.get("/resolve")
@jwt_required()
def resolve_exercise():
    """Resolve free-text input to a single canonical exercise."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"match": None})
    match = library_service.resolve(query)
    return jsonify({"match": match.to_dict() if match else None})


@library_bp.post("/custom")
@jwt_required()
def create_custom_exercise():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    primary_muscle = (data.get("primary_muscle") or "").strip()
    movement_pattern = (data.get("movement_pattern") or "").strip()
    # equipment may be a string or list
    equipment = data.get("equipment") or []
    if isinstance(equipment, str):
        equipment = equipment.strip()

    if not all([name, primary_muscle, equipment, movement_pattern]):
        return jsonify({"error": "name, primary_muscle, equipment, and movement_pattern are required"}), 400

    try:
        ex = library_service.add_custom(
            name=name,
            primary_muscle=primary_muscle,
            equipment=equipment,
            movement_pattern=movement_pattern,
            aliases=data.get("aliases", []),
            secondary_muscles=data.get("secondary_muscles", []),
            unilateral=bool(data.get("unilateral", False)),
            category=data.get("category"),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 409

    return jsonify(ex.to_dict()), 201


@library_bp.get("/categories")
@jwt_required()
def list_categories():
    """Return distinct filter values for the UI."""
    from backend.models.exercise_library import ExerciseLibrary
    import json

    def distinct_scalar(col):
        rows = (
            ExerciseLibrary.query
            .with_entities(col)
            .filter_by(is_active=True)
            .distinct()
            .order_by(col)
            .all()
        )
        return [r[0] for r in rows if r[0]]

    # equipment is now a JSON array — collect all unique values across all rows
    all_equipment: set[str] = set()
    rows = ExerciseLibrary.query.with_entities(ExerciseLibrary.equipment).filter_by(is_active=True).all()
    for (eq,) in rows:
        if not eq:
            continue
        vals = eq if isinstance(eq, list) else json.loads(eq)
        all_equipment.update(vals)

    return jsonify({
        "equipment": sorted(all_equipment),
        "movement_patterns": distinct_scalar(ExerciseLibrary.movement_pattern),
        "muscles": distinct_scalar(ExerciseLibrary.primary_muscle),
        "categories": distinct_scalar(ExerciseLibrary.category),
        "tiers": distinct_scalar(ExerciseLibrary.tier),
    })
