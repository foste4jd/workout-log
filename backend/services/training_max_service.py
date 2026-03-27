from backend.db.database import db
from backend.models.training_max import TrainingMax


def get_training_maxes(user_id):
    return (
        TrainingMax.query
        .filter_by(user_id=user_id)
        .join(TrainingMax.exercise)
        .order_by(db.text("exercise_library.name"))
        .all()
    )


def get_training_max(user_id, exercise_id):
    return TrainingMax.query.filter_by(user_id=user_id, exercise_id=exercise_id).first()


def upsert_training_max(user_id, exercise_id, weight, notes=None):
    record = TrainingMax.query.filter_by(user_id=user_id, exercise_id=exercise_id).first()
    if record:
        record.training_max_weight = weight
        if notes is not None:
            record.notes = notes
    else:
        record = TrainingMax(
            user_id=user_id,
            exercise_id=exercise_id,
            training_max_weight=weight,
            notes=notes,
        )
        db.session.add(record)
    db.session.commit()
    return record


def delete_training_max(record):
    db.session.delete(record)
    db.session.commit()


def get_training_max_map(user_id):
    """Returns {exercise_id: weight} for fast lookup."""
    maxes = TrainingMax.query.filter_by(user_id=user_id).all()
    return {m.exercise_id: m.training_max_weight for m in maxes}
