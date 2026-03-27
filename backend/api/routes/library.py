from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from backend.models.exercise_library import ExerciseLibrary

library_bp = Blueprint("library", __name__, url_prefix="/api/library")


@library_bp.get("/")
@jwt_required()
def list_exercises():
    exercises = (
        ExerciseLibrary.query
        .filter_by(is_active=True)
        .order_by(ExerciseLibrary.name)
        .all()
    )
    return jsonify([e.to_dict() for e in exercises])


@library_bp.get("/categories")
@jwt_required()
def list_categories():
    rows = (
        ExerciseLibrary.query
        .with_entities(ExerciseLibrary.category)
        .filter_by(is_active=True)
        .distinct()
        .order_by(ExerciseLibrary.category)
        .all()
    )
    return jsonify([r[0] for r in rows])
