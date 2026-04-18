"""Run this script to populate the database with sample data.

Usage:
    python seed.py
"""
from datetime import datetime
from backend.app import create_app
from backend.db.database import db
from backend.models.user import User
from backend.models.workout import Workout
from backend.models.exercise import Exercise
from backend.models.exercise_set import ExerciseSet
from backend.models.personal_max import PersonalMax
from flask_bcrypt import Bcrypt

app = create_app()
bcrypt = Bcrypt(app)


def d(date_str):
    return datetime.fromisoformat(date_str + "T12:00:00")


def sets5(weight_lb, reps=5, count=5):
    return [{"reps": reps, "weight_lb": weight_lb}] * count


def sets1(weight_lb, reps=5):
    return [{"reps": reps, "weight_lb": weight_lb}]


WORKOUTS = [
    {
        "date": "2026-03-03", "title": "5x5 — Workout A", "duration_minutes": 60,
        "notes": "First session. Kept weights conservative to nail form.",
        "exercises": [
            {"name": "Squat",         "sets": sets5(175)},
            {"name": "Bench Press",   "sets": sets5(135)},
            {"name": "Bent Over Row", "sets": sets5(120)},
        ],
    },
    {
        "date": "2026-03-05", "title": "5x5 — Workout B", "duration_minutes": 55,
        "notes": "Deadlift felt solid. OHP always humbles me.",
        "exercises": [
            {"name": "Squat",          "sets": sets5(185)},
            {"name": "Overhead Press", "sets": sets5(100)},
            {"name": "Deadlift",       "sets": sets1(225)},
        ],
    },
    {
        "date": "2026-03-07", "title": "5x5 — Workout A", "duration_minutes": 60,
        "notes": "Squat depth improving. Bench starting to feel heavier.",
        "exercises": [
            {"name": "Squat",         "sets": sets5(195)},
            {"name": "Bench Press",   "sets": sets5(140)},
            {"name": "Bent Over Row", "sets": sets5(125)},
        ],
    },
    {
        "date": "2026-03-10", "title": "5x5 — Workout B", "duration_minutes": 55,
        "notes": "Hit 205 squat for 5x5 — new PR. Deadlift moving well.",
        "exercises": [
            {"name": "Squat",          "sets": sets5(205)},
            {"name": "Overhead Press", "sets": sets5(105)},
            {"name": "Deadlift",       "sets": sets1(235)},
        ],
    },
    {
        "date": "2026-03-12", "title": "5x5 — Workout A", "duration_minutes": 65,
        "notes": "225 squat! Big milestone. Bench and rows feeling strong.",
        "exercises": [
            {"name": "Squat",         "sets": sets5(225)},
            {"name": "Bench Press",   "sets": sets5(145)},
            {"name": "Bent Over Row", "sets": sets5(130)},
        ],
    },
    {
        "date": "2026-03-14", "title": "5x5 — Workout B", "duration_minutes": 60,
        "notes": "OHP stalling soon probably. Deadlift feeling heavy but manageable.",
        "exercises": [
            {"name": "Squat",          "sets": sets5(235)},
            {"name": "Overhead Press", "sets": sets5(110)},
            {"name": "Deadlift",       "sets": sets1(245)},
        ],
    },
    {
        "date": "2026-03-17", "title": "5x5 — Workout A", "duration_minutes": 65,
        "notes": "245 squat — legs are growing. Bench at 150 went up clean.",
        "exercises": [
            {"name": "Squat",         "sets": sets5(245)},
            {"name": "Bench Press",   "sets": sets5(150)},
            {"name": "Bent Over Row", "sets": sets5(135)},
        ],
    },
    {
        "date": "2026-03-19", "title": "5x5 — Workout B", "duration_minutes": 60,
        "notes": "Struggled on last set of OHP. Squat continues to climb.",
        "exercises": [
            {"name": "Squat",          "sets": sets5(255)},
            {"name": "Overhead Press", "sets": sets5(115)},
            {"name": "Deadlift",       "sets": sets1(255)},
        ],
    },
    {
        "date": "2026-03-21", "title": "5x5 — Workout A", "duration_minutes": 70,
        "notes": "265 squat felt heavy but got all 25 reps. 155 bench — new PR.",
        "exercises": [
            {"name": "Squat",         "sets": sets5(265)},
            {"name": "Bench Press",   "sets": sets5(155)},
            {"name": "Bent Over Row", "sets": sets5(140)},
        ],
    },
    {
        "date": "2026-03-24", "title": "5x5 — Workout B", "duration_minutes": 65,
        "notes": "275 squat — grinding but got it. Deadlift at 275 moved well.",
        "exercises": [
            {"name": "Squat",          "sets": sets5(275)},
            {"name": "Overhead Press", "sets": sets5(120)},
            {"name": "Deadlift",       "sets": sets1(275)},
        ],
    },
]

PERSONAL_MAXES = [
    {"exercise_name": "Squat",          "weight_lb": 275},
    {"exercise_name": "Bench Press",    "weight_lb": 155},
    {"exercise_name": "Bent Over Row",  "weight_lb": 140},
    {"exercise_name": "Overhead Press", "weight_lb": 120},
    {"exercise_name": "Deadlift",       "weight_lb": 275},
]

with app.app_context():
    db.create_all()

    existing = User.query.filter_by(username="admin").first()
    if existing:
        # Clear workouts and personal maxes but keep the user record so its ID
        # doesn't change — templates are keyed to user_id and would become
        # orphaned if the user were deleted and re-created.
        for w in existing.workouts:
            db.session.delete(w)
        PersonalMax.query.filter_by(user_id=existing.id).delete()
        existing.password_hash = bcrypt.generate_password_hash("password").decode("utf-8")
        existing.email = "admin@example.com"
        db.session.commit()
        print("Cleared existing workout/max data (templates preserved).")
        user = existing
    else:
        password_hash = bcrypt.generate_password_hash("password").decode("utf-8")
        user = User(username="admin", email="admin@example.com", password_hash=password_hash)
        db.session.add(user)
        db.session.flush()

    for w in WORKOUTS:
        workout = Workout(
            user_id=user.id,
            title=w["title"],
            notes=w["notes"],
            duration_minutes=w["duration_minutes"],
            date=d(w["date"]),
        )
        db.session.add(workout)
        db.session.flush()

        for ex_data in w["exercises"]:
            exercise = Exercise(workout_id=workout.id, name=ex_data["name"])
            db.session.add(exercise)
            db.session.flush()
            for i, s in enumerate(ex_data["sets"], 1):
                db.session.add(ExerciseSet(
                    exercise_id=exercise.id,
                    set_number=i,
                    reps=s["reps"],
                    weight_lb=s["weight_lb"],
                ))

    for pm in PERSONAL_MAXES:
        db.session.add(PersonalMax(
            user_id=user.id,
            exercise_name=pm["exercise_name"],
            weight_lb=pm["weight_lb"],
            is_manual=True,
        ))

    db.session.commit()
    print("Seeded 10 workouts (StrongLifts 5x5, March 2026) with personal maxes.")
    print("  Username: admin")
    print("  Password: password")
