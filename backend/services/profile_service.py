from datetime import date as date_type
from backend.db.database import db
from backend.models.user_profile import UserProfile
from backend.models.bodyweight_entry import BodyweightEntry

_VALID_EXPERIENCE = {"beginner", "intermediate", "advanced", "elite"}
_VALID_GOALS = {"strength", "hypertrophy", "powerlifting", "general", "endurance"}
_VALID_INTENSITY = {"rpe", "percentage", "load", "auto"}


def get_or_create_profile(user_id: int) -> UserProfile:
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        db.session.commit()
    return profile


def update_profile(user_id: int, data: dict) -> tuple:
    profile = get_or_create_profile(user_id)
    errors = []

    if "experience_level" in data:
        val = data["experience_level"] or None
        if val and val not in _VALID_EXPERIENCE:
            errors.append(f"Invalid experience_level")
        else:
            profile.experience_level = val

    if "primary_goal" in data:
        val = data["primary_goal"] or None
        if val and val not in _VALID_GOALS:
            errors.append("Invalid primary_goal")
        else:
            profile.primary_goal = val

    if "training_frequency_target" in data:
        val = data["training_frequency_target"]
        if val is None or val == "":
            profile.training_frequency_target = None
        else:
            try:
                val = int(val)
                if not (1 <= val <= 7):
                    errors.append("training_frequency_target must be 1–7")
                else:
                    profile.training_frequency_target = val
            except (TypeError, ValueError):
                errors.append("training_frequency_target must be an integer")

    if "preferred_intensity_style" in data:
        val = data["preferred_intensity_style"] or None
        if val and val not in _VALID_INTENSITY:
            errors.append("Invalid preferred_intensity_style")
        else:
            profile.preferred_intensity_style = val

    if "movement_restrictions" in data:
        profile.movement_restrictions = (data["movement_restrictions"] or "").strip() or None

    if not errors:
        db.session.commit()

    return profile, errors


def add_bodyweight_entry(
    user_id: int,
    weight_kg: float,
    recorded_date: date_type,
    notes: str = None,
) -> BodyweightEntry:
    entry = BodyweightEntry(
        user_id=user_id,
        weight_kg=round(weight_kg, 4),
        recorded_date=recorded_date,
        notes=(notes or "").strip() or None,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def get_bodyweight_history(user_id: int, limit: int = 30) -> list:
    return (
        BodyweightEntry.query
        .filter_by(user_id=user_id)
        .order_by(BodyweightEntry.recorded_date.desc())
        .limit(limit)
        .all()
    )


def get_latest_bodyweight(user_id: int):
    return (
        BodyweightEntry.query
        .filter_by(user_id=user_id)
        .order_by(BodyweightEntry.recorded_date.desc())
        .first()
    )


def get_profile_context(user_id: int) -> dict:
    """Return a compact dict suitable for injecting into AI prompt context."""
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    latest_bw = get_latest_bodyweight(user_id)
    if not profile:
        return {}
    return {
        k: v for k, v in {
            "experience_level": profile.experience_level,
            "primary_goal": profile.primary_goal,
            "training_frequency_target": profile.training_frequency_target,
            "preferred_intensity_style": profile.preferred_intensity_style,
            "movement_restrictions": profile.movement_restrictions,
            "current_bodyweight_kg": latest_bw.weight_kg if latest_bw else None,
        }.items() if v is not None
    }
