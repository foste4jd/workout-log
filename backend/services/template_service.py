from datetime import datetime, timezone
from backend.db.database import db
from backend.models.workout import Workout
from backend.models.exercise import Exercise
from backend.models.exercise_set import ExerciseSet
from backend.models.workout_template import WorkoutTemplate, WorkoutTemplateExercise, WorkoutTemplateSet


# ── Template CRUD ─────────────────────────────────────────────────────────────

def get_templates(user_id):
    return (
        WorkoutTemplate.query
        .filter_by(user_id=user_id)
        .order_by(WorkoutTemplate.name)
        .all()
    )


def get_template(template_id, user_id):
    return WorkoutTemplate.query.filter_by(id=template_id, user_id=user_id).first()


def create_template(user_id, data):
    template = WorkoutTemplate(
        user_id=user_id,
        name=data["name"],
        description=data.get("description"),
    )
    db.session.add(template)
    db.session.flush()
    _replace_exercises(template, data.get("exercises", []))
    db.session.commit()
    return template


def update_template(template, data):
    template.name = data.get("name", template.name)
    template.description = data.get("description", template.description)
    if "exercises" in data:
        for ex in list(template.exercises):
            db.session.delete(ex)
        db.session.flush()
        _replace_exercises(template, data["exercises"])
    db.session.commit()
    return template


def delete_template(template):
    db.session.delete(template)
    db.session.commit()


def _replace_exercises(template, exercises_data):
    for i, ex_data in enumerate(exercises_data):
        te = WorkoutTemplateExercise(
            template_id=template.id,
            exercise_id=ex_data["exercise_id"],
            order_index=i,
            notes=ex_data.get("notes"),
        )
        db.session.add(te)
        db.session.flush()
        for j, s in enumerate(ex_data.get("sets", []), 1):
            db.session.add(WorkoutTemplateSet(
                template_exercise_id=te.id,
                set_number=j,
                set_type=s.get("set_type", "working"),
                reps=s.get("reps"),
                weight=s.get("weight"),
                percent=s.get("percent"),
                duration_seconds=s.get("duration_seconds"),
            ))


# ── Create session from template ──────────────────────────────────────────────

def create_session_from_template(template, user_id, date=None):
    """Snapshot the template into a standalone WorkoutSession. Template changes
    after this point do NOT affect the session."""
    session = Workout(
        user_id=user_id,
        title=template.name,
        status="planned",
        template_id=template.id,
        date=_parse_date(date),
    )
    db.session.add(session)
    db.session.flush()

    for te in sorted(template.exercises, key=lambda x: x.order_index):
        ex = Exercise(
            workout_id=session.id,
            exercise_library_id=te.exercise_id,
            name=te.exercise.name,
            notes=te.notes,
        )
        db.session.add(ex)
        db.session.flush()
        for ts in sorted(te.sets, key=lambda x: x.set_number):
            db.session.add(ExerciseSet(
                exercise_id=ex.id,
                set_number=ts.set_number,
                set_type=ts.set_type or "working",
                reps=ts.reps,
                weight_lb=ts.weight,
                percent=ts.percent,
                duration_seconds=ts.duration_seconds,
                completed=False,
            ))

    db.session.commit()
    return session


# ── Copy prior workout ────────────────────────────────────────────────────────

def copy_session(source_workout, user_id, date=None):
    """Copy a completed session into a new planned session. Planned values are
    taken from the source's actual logged values."""
    new_session = Workout(
        user_id=user_id,
        title=source_workout.title,
        status="planned",
        date=_parse_date(date),
    )
    db.session.add(new_session)
    db.session.flush()

    for ex in source_workout.exercises:
        new_ex = Exercise(
            workout_id=new_session.id,
            exercise_library_id=ex.exercise_library_id,
            name=ex.name,
        )
        db.session.add(new_ex)
        db.session.flush()
        for s in ex.set_records:
            db.session.add(ExerciseSet(
                exercise_id=new_ex.id,
                set_number=s.set_number,
                set_type=s.set_type,
                reps=s.reps,
                weight_lb=s.weight_lb,
                percent=s.percent,
                duration_seconds=s.duration_seconds,
                completed=False,
            ))

    db.session.commit()
    return new_session


def create_template_from_workout(user_id, workout, name, description=None):
    """Create a template from an existing logged workout."""
    exercises_data = []
    for ex in workout.exercises:
        if not ex.exercise_library_id:
            continue  # skip free-text exercises not linked to the library
        exercises_data.append({
            "exercise_id": ex.exercise_library_id,
            "notes": ex.notes,
            "sets": [
                {
                    "set_type": s.set_type,
                    "reps": s.reps,
                    "weight": s.weight_lb,
                    "percent": s.percent,
                }
                for s in ex.set_records
            ],
        })
    return create_template(user_id, {
        "name": name,
        "description": description,
        "exercises": exercises_data,
    })


def _parse_date(date_str):
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return datetime.now(timezone.utc)
