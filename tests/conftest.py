"""
Shared fixtures for the WorkoutLog test suite.

Uses an in-memory SQLite database so tests never touch workouts.db.
The OpenAI API is mocked in all tests — no real API calls are made.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from backend.app import create_app
from backend.db.database import db as _db


@pytest.fixture(scope="session")
def app():
    """Create application with in-memory test database."""
    test_app = create_app()
    test_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "SECRET_KEY": "test-secret",
    })
    with test_app.app_context():
        _db.create_all()
        _seed_library(test_app)
        yield test_app
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    """Fresh DB state per test — rolls back after each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def auth_headers(client, app):
    """Register + login a test user, return JWT headers."""
    with app.app_context():
        client.post("/api/users/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
        })
        resp = client.post("/api/users/login", json={
            "username": "testuser",
            "password": "testpass123",
        })
        token = resp.get_json()["token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def user_id(client, auth_headers, app):
    """Return the id of the logged-in test user."""
    with app.app_context():
        from backend.models.user import User
        u = User.query.filter_by(username="testuser").first()
        return u.id


@pytest.fixture
def mock_openai():
    """
    Patch the OpenAI client so no real API calls are made.
    Returns a factory: call mock_openai(result_dict) to set the response.
    """
    def _make_mock(response_dict):
        mock_choice  = MagicMock()
        mock_choice.message.content = json.dumps(response_dict)
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        return mock_client

    with patch("backend.services.ai_trainer_service.OpenAIProvider.__init__",
               return_value=None) as _:
        with patch("backend.services.ai_trainer_service.OpenAIProvider.complete") as mock_complete:
            yield mock_complete

    return mock_complete


def _seed_library(app):
    """Seed a small exercise library for tests."""
    from backend.models.exercise_library import ExerciseLibrary
    exercises = [
        ("Back Squat",     "Squat"),
        ("Bench Press",    "Press"),
        ("Deadlift",       "Hinge"),
        ("Overhead Press", "Press"),
        ("Bent Over Row",  "Pull"),
        ("Romanian Deadlift", "Hinge"),
        ("Pull-up",        "Pull"),
        ("Barbell Curl",   "Arms"),
    ]
    for name, cat in exercises:
        if not ExerciseLibrary.query.filter_by(name=name).first():
            _db.session.add(ExerciseLibrary(name=name, category=cat))
    _db.session.commit()


# ── Shared AI result fixtures ──────────────────────────────────────────────────

WORKOUT_RESULT = {
    "mode": "workout",
    "workout_name": "Heavy Lower",
    "workout_goal": "Strength — main lift progression",
    "summary": "Squat hasn't been trained in 3 days. Good day to go heavy.",
    "ai_noticed": ["Back squat trending up 4 sessions"],
    "memory_candidates": [],
    "training_max_recommendations": [],
    "workout": {
        "name": "Heavy Lower",
        "exercises": [
            {
                "exercise_name": "Back Squat",
                "notes": None,
                "blocks": [
                    {"set_type": "warmup",  "sets": 2, "reps": 5,  "percent": 50, "weight": None},
                    {"set_type": "working", "sets": 3, "reps": 5,  "percent": 75, "weight": None},
                    {"set_type": "amrap",   "sets": 1, "reps": None, "percent": 80, "weight": None},
                ],
            },
            {
                "exercise_name": "Romanian Deadlift",
                "notes": "Control the descent",
                "blocks": [
                    {"set_type": "working", "sets": 4, "reps": 8, "weight": 185, "percent": None},
                ],
            },
        ],
    },
    "answer": None,
}

ANSWER_RESULT = {
    "mode": "answer",
    "workout_name": None,
    "workout_goal": None,
    "summary": "Deload weeks should cut volume 40-60% while keeping intensity above 70%.",
    "ai_noticed": [],
    "memory_candidates": [
        {"category": "preferences", "text": "Prefers deload every 4 weeks", "priority": "medium"}
    ],
    "training_max_recommendations": [],
    "workout": None,
    "answer": {
        "title": "Deload Programming",
        "content": "Cut sets by half, keep weight above 70% of TM.",
        "suggested_action": "none",
    },
}
