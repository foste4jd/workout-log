from backend.db.database import db
from backend.models.personal_max import PersonalMax


def get_maxes(user_id):
    return PersonalMax.query.filter_by(user_id=user_id).order_by(PersonalMax.exercise_name).all()


def upsert_max(user_id, exercise_name, weight_lb):
    record = PersonalMax.query.filter_by(user_id=user_id, exercise_name=exercise_name).first()
    if record:
        record.weight_lb = weight_lb
        record.is_manual = True
    else:
        record = PersonalMax(user_id=user_id, exercise_name=exercise_name, weight_lb=weight_lb, is_manual=True)
        db.session.add(record)
    db.session.commit()
    return record


def delete_max(record):
    db.session.delete(record)
    db.session.commit()