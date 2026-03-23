"""Run this script to populate the database with sample data.

Usage:
    python seed.py
"""
from datetime import datetime, timezone, timedelta
from backend.app import create_app
from backend.db.database import db
from backend.models.user import User
from backend.models.workout import Workout
from flask_bcrypt import Bcrypt

app = create_app()
bcrypt = Bcrypt(app)

SAMPLE_WORKOUTS = [
    {
        "title": "Morning Run",
        "notes": "Easy 5k around the park. Felt good, legs a bit stiff at the start.",
        "duration_minutes": 28,
        "days_ago": 1,
    },
    {
        "title": "Upper Body Strength",
        "notes": "Bench 3x8 @ 80kg, OHP 3x10 @ 50kg, rows 3x10. Hit a new bench PR!",
        "duration_minutes": 55,
        "days_ago": 3,
    },
    {
        "title": "Cycling",
        "notes": "20 mile ride on the trail. Avg HR 145bpm.",
        "duration_minutes": 75,
        "days_ago": 5,
    },
    {
        "title": "Leg Day",
        "notes": "Squats 4x6 @ 100kg, Romanian deadlifts 3x10, leg press, calf raises.",
        "duration_minutes": 60,
        "days_ago": 7,
    },
    {
        "title": "HIIT Session",
        "notes": "20 min tabata — burpees, jump squats, mountain climbers. Brutal.",
        "duration_minutes": 20,
        "days_ago": 9,
    },
    {
        "title": "Yoga & Mobility",
        "notes": "30 min yoga flow focusing on hip flexors and thoracic spine.",
        "duration_minutes": 30,
        "days_ago": 11,
    },
    {
        "title": "Pull Day",
        "notes": "Deadlifts 3x5 @ 120kg, pull-ups 4x8, cable rows, face pulls.",
        "duration_minutes": 50,
        "days_ago": 14,
    },
]

with app.app_context():
    db.create_all()

    if User.query.filter_by(email="demo@example.com").first():
        print("Sample data already exists. Skipping.")
    else:
        password_hash = bcrypt.generate_password_hash("password123").decode("utf-8")
        user = User(username="demo", email="demo@example.com", password_hash=password_hash)
        db.session.add(user)
        db.session.flush()

        for w in SAMPLE_WORKOUTS:
            workout = Workout(
                user_id=user.id,
                title=w["title"],
                notes=w["notes"],
                duration_minutes=w["duration_minutes"],
                date=datetime.now(timezone.utc) - timedelta(days=w["days_ago"]),
            )
            db.session.add(workout)

        db.session.commit()
        print("Sample data created.")
        print("  Email:    demo@example.com")
        print("  Password: password123")
