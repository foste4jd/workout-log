"""Unit tests — context builder, recency map, trend detection, block expansion."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from backend.services.ai_trainer_service import (
    _build_recency_map,
    _build_trends,
    _blocks_to_sets,
    _text_similarity,
    build_context,
    _build_user_message,
)


# ── build_context ──────────────────────────────────────────────────────────────

def test_build_context_returns_required_keys(app, db, user_id):
    with app.app_context():
        ctx = build_context(user_id)
        for key in ("today", "training_maxes", "recency", "trends",
                    "week_count", "recent_workouts", "older_workouts", "memories"):
            assert key in ctx, f"Missing context key: {key}"


def test_build_context_training_maxes_empty_without_data(app, db, user_id):
    with app.app_context():
        ctx = build_context(user_id)
        # No TMs seeded for this user — should be empty dict not error
        assert isinstance(ctx["training_maxes"], dict)


def test_build_context_recency_has_all_patterns(app, db, user_id):
    with app.app_context():
        ctx = build_context(user_id)
        expected_patterns = [
            "squat", "hinge", "horizontal_push", "vertical_push",
            "horizontal_pull", "vertical_pull", "arms", "carry", "core",
        ]
        for p in expected_patterns:
            assert p in ctx["recency"], f"Missing recency pattern: {p}"


def test_build_context_week_count_is_non_negative(app, db, user_id):
    with app.app_context():
        ctx = build_context(user_id)
        assert ctx["week_count"] >= 0


def test_build_user_message_contains_prompt(app, db, user_id):
    with app.app_context():
        ctx = build_context(user_id)
        msg = _build_user_message(ctx, "heavy leg day please")
        assert "heavy leg day please" in msg


def test_build_user_message_blank_prompt_uses_fallback(app, db, user_id):
    with app.app_context():
        ctx = build_context(user_id)
        msg = _build_user_message(ctx, "")
        assert "no prompt" in msg.lower()


def test_build_user_message_contains_today(app, db, user_id):
    with app.app_context():
        ctx = build_context(user_id)
        msg = _build_user_message(ctx, "test")
        assert "TODAY:" in msg


# ── _build_recency_map ─────────────────────────────────────────────────────────

def _make_lib(name, cat):
    lib = MagicMock()
    lib.name = name
    lib.category = cat
    return lib


def _make_mock_workout(exercises_with_patterns, days_ago):
    """Build a minimal mock workout object for recency/trend testing."""
    w = MagicMock()
    w.date = datetime.utcnow() - timedelta(days=days_ago)
    w.title = "Test Workout"
    w.duration_minutes = 60

    mock_exercises = []
    for idx, (name, cat) in enumerate(exercises_with_patterns):
        ex = MagicMock()
        ex.name = name
        ex.exercise_library_id = idx + 1  # truthy so the lookup fires
        ex.exercise_library = _make_lib(name, cat)

        s = MagicMock()
        s.set_type = "working"
        s.reps = 5
        s.weight_lb = 225.0
        s.percent = 75.0
        s.completed = True
        ex.set_records = [s, s, s]
        mock_exercises.append(ex)

    w.exercises = mock_exercises
    return w


def _patch_lib_lookup(name, cat):
    """Return a context manager that patches ExerciseLibrary.query.get."""
    return patch(
        "backend.services.ai_trainer_service.ExerciseLibrary.query",
        **{"get.return_value": _make_lib(name, cat)},
    )


def test_recency_map_returns_none_for_untrained(app):
    with app.app_context():
        recency = _build_recency_map([])
        assert all(v is None for v in recency.values())


def test_recency_map_correct_days(app):
    with app.app_context():
        with _patch_lib_lookup("Back Squat", "Squat"):
            workouts = [_make_mock_workout([("Back Squat", "Squat")], days_ago=2)]
            recency = _build_recency_map(workouts)
        assert recency["squat"] == 2


def test_recency_map_most_recent_wins(app):
    with app.app_context():
        with _patch_lib_lookup("Back Squat", "Squat"):
            workouts = [
                _make_mock_workout([("Back Squat", "Squat")], days_ago=1),
                _make_mock_workout([("Back Squat", "Squat")], days_ago=5),
            ]
            recency = _build_recency_map(workouts)
        assert recency["squat"] == 1


def test_recency_map_hinge_pattern(app):
    with app.app_context():
        with _patch_lib_lookup("Deadlift", "Hinge"):
            workouts = [_make_mock_workout([("Deadlift", "Hinge")], days_ago=3)]
            recency = _build_recency_map(workouts)
        assert recency["hinge"] == 3


# ── _build_trends ──────────────────────────────────────────────────────────────

def _make_workout_with_weight(name, weight, days_ago, completed=True):
    w = MagicMock()
    w.date = datetime.utcnow() - timedelta(days=days_ago)
    w.title = "Test"
    w.duration_minutes = 60

    ex = MagicMock()
    ex.name = name
    ex.exercise_library_id = None

    sets = []
    for _ in range(3):
        s = MagicMock()
        s.set_type = "working"
        s.reps = 5
        s.weight_lb = weight
        s.percent = None
        s.completed = completed
        sets.append(s)
    ex.set_records = sets
    w.exercises = [ex]
    return w


def test_trends_progressing(app):
    with app.app_context():
        workouts = [
            _make_workout_with_weight("Bench Press", 225, days_ago=1),
            _make_workout_with_weight("Bench Press", 205, days_ago=8),
        ]
        trends = _build_trends(workouts)
        assert "Bench Press" in trends
        assert trends["Bench Press"]["trend"] == "progressing"


def test_trends_stalled(app):
    with app.app_context():
        workouts = [
            _make_workout_with_weight("Bench Press", 225, days_ago=1),
            _make_workout_with_weight("Bench Press", 225, days_ago=8),
        ]
        trends = _build_trends(workouts)
        assert trends["Bench Press"]["trend"] == "stalled"


def test_trends_declining(app):
    with app.app_context():
        workouts = [
            _make_workout_with_weight("Bench Press", 185, days_ago=1),
            _make_workout_with_weight("Bench Press", 225, days_ago=8),
        ]
        trends = _build_trends(workouts)
        assert trends["Bench Press"]["trend"] == "declining"


def test_trends_missed_reps_flag(app):
    with app.app_context():
        workouts = [_make_workout_with_weight("Back Squat", 315, days_ago=1, completed=False)]
        trends = _build_trends(workouts)
        assert trends["Back Squat"]["missed_last"] is True


def test_trends_no_missed_reps(app):
    with app.app_context():
        workouts = [_make_workout_with_weight("Back Squat", 315, days_ago=1, completed=True)]
        trends = _build_trends(workouts)
        assert trends["Back Squat"]["missed_last"] is False


def test_trends_insufficient_data_single_session(app):
    with app.app_context():
        workouts = [_make_workout_with_weight("Overhead Press", 135, days_ago=1)]
        trends = _build_trends(workouts)
        assert trends["Overhead Press"]["trend"] == "insufficient_data"


# ── _blocks_to_sets ────────────────────────────────────────────────────────────

def test_blocks_to_sets_expands_count(app, db):
    with app.app_context():
        blocks = [{"set_type": "working", "sets": 3, "reps": 5, "weight": 225, "percent": None}]
        sets = _blocks_to_sets(blocks, lib_entry=None, user_id=1)
        assert len(sets) == 3


def test_blocks_to_sets_set_numbers_sequential(app, db):
    with app.app_context():
        blocks = [
            {"set_type": "warmup",  "sets": 2, "reps": 5, "weight": 135, "percent": None},
            {"set_type": "working", "sets": 3, "reps": 5, "weight": 225, "percent": None},
        ]
        sets = _blocks_to_sets(blocks, lib_entry=None, user_id=1)
        assert len(sets) == 5
        nums = [s["set_number"] for s in sets]
        assert nums == list(range(1, 6))


def test_blocks_to_sets_percent_resolved_with_tm(app, db, user_id):
    with app.app_context():
        from backend.models.training_max import TrainingMax
        from backend.models.exercise_library import ExerciseLibrary

        lib = ExerciseLibrary.query.filter_by(name="Back Squat").first()
        db.session.add(TrainingMax(
            user_id=user_id, exercise_id=lib.id, training_max_weight=300.0
        ))
        db.session.commit()

        blocks = [{"set_type": "working", "sets": 1, "reps": 5, "percent": 75, "weight": None}]
        sets = _blocks_to_sets(blocks, lib_entry=lib, user_id=user_id)

        # 75% of 300 = 225, rounded to nearest 2.5
        assert sets[0]["weight_lb"] == 225.0
        assert sets[0]["percent"] == 75


def test_blocks_to_sets_percent_without_tm_stays_null(app, db, user_id):
    with app.app_context():
        from backend.models.exercise_library import ExerciseLibrary
        lib = ExerciseLibrary.query.filter_by(name="Overhead Press").first()
        # No TM set for this exercise
        blocks = [{"set_type": "working", "sets": 1, "reps": 5, "percent": 75, "weight": None}]
        sets = _blocks_to_sets(blocks, lib_entry=lib, user_id=user_id)
        assert sets[0]["weight_lb"] is None


def test_blocks_to_sets_handles_non_numeric_reps(app, db):
    with app.app_context():
        blocks = [{"set_type": "amrap", "sets": 1, "reps": "max", "weight": 225, "percent": None}]
        sets = _blocks_to_sets(blocks, lib_entry=None, user_id=1)
        assert sets[0]["reps"] is None  # non-numeric → None


def test_blocks_to_sets_empty_blocks(app, db):
    with app.app_context():
        sets = _blocks_to_sets([], lib_entry=None, user_id=1)
        assert sets == []
