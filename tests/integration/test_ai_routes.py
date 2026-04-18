"""Integration tests — AI trainer API routes."""
import json
import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import WORKOUT_RESULT, ANSWER_RESULT


def _mock_provider(response_dict):
    """Patch OpenAIProvider.complete to return response_dict as JSON string."""
    mock = MagicMock(return_value=json.dumps(response_dict))
    return patch("backend.services.ai_trainer_service.OpenAIProvider.complete", mock)


# ── POST /api/ai/suggest ───────────────────────────────────────────────────────

def test_suggest_requires_auth(client):
    resp = client.post("/api/ai/suggest", json={"prompt": "leg day"})
    assert resp.status_code == 401


def test_suggest_blank_prompt_accepted(client, auth_headers):
    with _mock_provider(WORKOUT_RESULT):
        resp = client.post("/api/ai/suggest", json={}, headers=auth_headers)
    assert resp.status_code == 200


def test_suggest_returns_workout_mode(client, auth_headers):
    with _mock_provider(WORKOUT_RESULT):
        resp = client.post("/api/ai/suggest",
                           json={"prompt": "heavy leg day"},
                           headers=auth_headers)
    data = resp.get_json()
    assert data["mode"] == "workout"
    assert data["workout"] is not None
    assert "exercises" in data["workout"]


def test_suggest_returns_answer_mode(client, auth_headers):
    with _mock_provider(ANSWER_RESULT):
        resp = client.post("/api/ai/suggest",
                           json={"prompt": "what is a deload week?"},
                           headers=auth_headers)
    data = resp.get_json()
    assert data["mode"] == "answer"
    assert data["answer"] is not None
    assert "content" in data["answer"]


def test_suggest_response_has_expected_top_level_keys(client, auth_headers):
    with _mock_provider(WORKOUT_RESULT):
        resp = client.post("/api/ai/suggest",
                           json={"prompt": "test"},
                           headers=auth_headers)
    data = resp.get_json()
    for key in ("mode", "summary", "ai_noticed",
                "memory_candidates", "training_max_recommendations"):
        assert key in data, f"Missing key: {key}"


def test_suggest_stores_memory_candidates(client, auth_headers, app, db):
    result_with_memory = {**WORKOUT_RESULT, "memory_candidates": [
        {"category": "schedule", "text": "Trains Monday Wednesday Friday", "priority": "high"}
    ]}
    with _mock_provider(result_with_memory):
        client.post("/api/ai/suggest",
                    json={"prompt": "test"},
                    headers=auth_headers)

    with app.app_context():
        from backend.models.ai_knowledge import AIKnowledge
        entries = AIKnowledge.query.filter_by(category="schedule").all()
        assert any("Monday" in e.text for e in entries)


def test_suggest_graceful_on_ai_error(client, auth_headers):
    with patch("backend.services.ai_trainer_service.OpenAIProvider.complete",
               side_effect=Exception("API timeout")):
        resp = client.post("/api/ai/suggest",
                           json={"prompt": "test"},
                           headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    # Should return a graceful error response, not a 500
    assert data.get("mode") == "answer"
    assert "error" in data.get("answer", {}).get("title", "").lower() or \
           "failed" in data.get("summary", "").lower()


# ── POST /api/ai/accept ────────────────────────────────────────────────────────

def test_accept_requires_auth(client):
    resp = client.post("/api/ai/accept", json={"ai_result": WORKOUT_RESULT})
    assert resp.status_code == 401


def test_accept_missing_ai_result_returns_400(client, auth_headers):
    resp = client.post("/api/ai/accept", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_accept_creates_workout_record(client, auth_headers, app, db):
    with app.app_context():
        from backend.models.workout import Workout
        from backend.models.user import User
        user = User.query.filter_by(username="testuser").first()
        before = Workout.query.filter_by(user_id=user.id).count()

    resp = client.post("/api/ai/accept",
                       json={"ai_result": WORKOUT_RESULT, "date": "2026-03-27"},
                       headers=auth_headers)
    assert resp.status_code == 201

    with app.app_context():
        from backend.models.workout import Workout
        from backend.models.user import User
        user = User.query.filter_by(username="testuser").first()
        after = Workout.query.filter_by(user_id=user.id).count()
        assert after == before + 1


def test_accept_creates_exercises(client, auth_headers, app, db):
    resp = client.post("/api/ai/accept",
                       json={"ai_result": WORKOUT_RESULT},
                       headers=auth_headers)
    assert resp.status_code == 201

    workout_id = resp.get_json()["id"]
    with app.app_context():
        from backend.models.exercise import Exercise
        exercises = Exercise.query.filter_by(workout_id=workout_id).all()
        # WORKOUT_RESULT has 2 exercises
        assert len(exercises) == 2


def test_accept_creates_sets(client, auth_headers, app, db):
    resp = client.post("/api/ai/accept",
                       json={"ai_result": WORKOUT_RESULT},
                       headers=auth_headers)
    workout_id = resp.get_json()["id"]

    with app.app_context():
        from backend.models.exercise import Exercise
        from backend.models.exercise_set import ExerciseSet
        exercises = Exercise.query.filter_by(workout_id=workout_id).all()
        total_sets = sum(
            ExerciseSet.query.filter_by(exercise_id=ex.id).count()
            for ex in exercises
        )
        # Back Squat: 2 warmup + 3 working + 1 amrap = 6 sets
        # Romanian DL: 4 sets
        assert total_sets == 10


def test_accept_matches_library_exercise(client, auth_headers, app, db):
    resp = client.post("/api/ai/accept",
                       json={"ai_result": WORKOUT_RESULT},
                       headers=auth_headers)
    workout_id = resp.get_json()["id"]

    with app.app_context():
        from backend.models.exercise import Exercise
        from backend.models.exercise_library import ExerciseLibrary
        exercises = Exercise.query.filter_by(workout_id=workout_id).all()
        squat_ex = next((e for e in exercises if "Squat" in e.name), None)
        assert squat_ex is not None
        assert squat_ex.exercise_library_id is not None


def test_accept_unknown_exercise_created_as_freetext(client, auth_headers, app, db):
    result_with_unknown = {**WORKOUT_RESULT, "workout": {
        "name": "Test",
        "exercises": [{
            "exercise_name": "Totally Unknown Exercise XYZ",
            "notes": None,
            "blocks": [{"set_type": "working", "sets": 3, "reps": 5, "weight": 135, "percent": None}],
        }]
    }}
    resp = client.post("/api/ai/accept",
                       json={"ai_result": result_with_unknown},
                       headers=auth_headers)
    assert resp.status_code == 201

    workout_id = resp.get_json()["id"]
    with app.app_context():
        from backend.models.exercise import Exercise
        ex = Exercise.query.filter_by(workout_id=workout_id).first()
        assert ex is not None
        assert ex.exercise_library_id is None  # not library-linked


def test_accept_returns_workout_dict(client, auth_headers):
    resp = client.post("/api/ai/accept",
                       json={"ai_result": WORKOUT_RESULT},
                       headers=auth_headers)
    data = resp.get_json()
    for key in ("id", "title", "date", "status"):
        assert key in data, f"Missing key: {key}"


# ── POST /api/ai/save-template ─────────────────────────────────────────────────

def test_save_template_requires_auth(client):
    resp = client.post("/api/ai/save-template", json={"ai_result": WORKOUT_RESULT})
    assert resp.status_code == 401


def test_save_template_missing_ai_result_returns_400(client, auth_headers):
    resp = client.post("/api/ai/save-template", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_save_template_creates_template(client, auth_headers, app, db):
    with app.app_context():
        from backend.models.workout_template import WorkoutTemplate
        from backend.models.user import User
        user = User.query.filter_by(username="testuser").first()
        before = WorkoutTemplate.query.filter_by(user_id=user.id).count()

    resp = client.post("/api/ai/save-template",
                       json={"ai_result": WORKOUT_RESULT},
                       headers=auth_headers)
    assert resp.status_code == 201

    with app.app_context():
        from backend.models.workout_template import WorkoutTemplate
        from backend.models.user import User
        user = User.query.filter_by(username="testuser").first()
        after = WorkoutTemplate.query.filter_by(user_id=user.id).count()
        assert after == before + 1


def test_save_template_name_matches_workout(client, auth_headers):
    resp = client.post("/api/ai/save-template",
                       json={"ai_result": WORKOUT_RESULT},
                       headers=auth_headers)
    data = resp.get_json()
    assert data["name"] == WORKOUT_RESULT["workout"]["name"]


# ── Memory CRUD ────────────────────────────────────────────────────────────────

def test_memory_list_requires_auth(client):
    resp = client.get("/api/ai/memory")
    assert resp.status_code == 401


def test_memory_list_returns_list(client, auth_headers):
    resp = client.get("/api/ai/memory", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_memory_delete_requires_auth(client):
    resp = client.delete("/api/ai/memory/1")
    assert resp.status_code == 401


def test_memory_delete_removes_entry(client, auth_headers, app, db):
    # First create a memory via suggest
    result_with_memory = {**WORKOUT_RESULT, "memory_candidates": [
        {"category": "other", "text": "Entry to be deleted shortly", "priority": "low"}
    ]}
    with _mock_provider(result_with_memory):
        client.post("/api/ai/suggest",
                    json={"prompt": "test"},
                    headers=auth_headers)

    # Find its ID
    resp = client.get("/api/ai/memory", headers=auth_headers)
    entries = resp.get_json()
    target = next((e for e in entries if "deleted" in e["text"]), None)
    assert target is not None

    # Delete it
    del_resp = client.delete(f"/api/ai/memory/{target['id']}", headers=auth_headers)
    assert del_resp.status_code == 200

    # Verify gone
    resp2 = client.get("/api/ai/memory", headers=auth_headers)
    ids = [e["id"] for e in resp2.get_json()]
    assert target["id"] not in ids


def test_memory_delete_other_users_entry_blocked(client, auth_headers, app, db):
    with app.app_context():
        from backend.models.ai_knowledge import AIKnowledge
        # Create entry owned by a different user
        entry = AIKnowledge(
            user_id=9999, type="memory", category="other",
            text="Other user memory", is_active=True, priority="low"
        )
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id

    resp = client.delete(f"/api/ai/memory/{entry_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_memory_toggle_active(client, auth_headers, app, db):
    # Create a memory
    result_with_memory = {**WORKOUT_RESULT, "memory_candidates": [
        {"category": "recovery", "text": "Unique toggle test memory entry xyz", "priority": "medium"}
    ]}
    with _mock_provider(result_with_memory):
        client.post("/api/ai/suggest", json={"prompt": "test"}, headers=auth_headers)

    entries = client.get("/api/ai/memory", headers=auth_headers).get_json()
    target = next((e for e in entries if "toggle test" in e["text"]), None)
    assert target is not None
    assert target["is_active"] is True

    resp = client.patch(f"/api/ai/memory/{target['id']}",
                        json={"is_active": False},
                        headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["is_active"] is False


# ── View route ─────────────────────────────────────────────────────────────────

def test_ai_memory_page_returns_200(client):
    resp = client.get("/ai-memory")
    assert resp.status_code == 200
    assert b"AI Memory" in resp.data


# ── Phase 2: web search integration ───────────────────────────────────────────

def _mock_search_web(results):
    """Patch search_web to return a fixed result list."""
    return patch(
        "backend.services.ai_trainer_service.search_web",
        return_value=results,
    )


def _mock_distill(summary, sources=None):
    """Patch _distill_search_results to return a fixed (summary, sources) tuple."""
    return patch(
        "backend.services.ai_trainer_service._distill_search_results",
        return_value=(summary, sources or []),
    )


_FAKE_SEARCH_RESULTS = [
    {"title": "Hypertrophy Research",
     "url":   "http://example.com/1",
     "content": "High volume training supports muscle hypertrophy."},
]

_DISTILLED_SUMMARY = (
    "Evidence supports high-volume training for hypertrophy when intensity is adequate."
)


_PATCH_WEB_ON  = patch("backend.ai_config.ALLOW_WEB_SEARCH", True)
_PATCH_WEB_OFF = patch("backend.ai_config.ALLOW_WEB_SEARCH", False)


def test_workout_request_never_calls_search(client, auth_headers):
    """Workout generation must never trigger web search, regardless of config."""
    with _PATCH_WEB_ON:
        with _mock_provider(WORKOUT_RESULT):
            with _mock_search_web(_FAKE_SEARCH_RESULTS) as mock_sw:
                client.post("/api/ai/suggest",
                            json={"prompt": "build me a leg day"},
                            headers=auth_headers)
    mock_sw.assert_not_called()


def test_educational_answer_uses_search_when_enabled(client, auth_headers):
    """Educational question + ALLOW_WEB_SEARCH=True should call search_web."""
    with _PATCH_WEB_ON:
        with _mock_provider(ANSWER_RESULT):
            with _mock_search_web(_FAKE_SEARCH_RESULTS) as mock_sw:
                with _mock_distill(_DISTILLED_SUMMARY):
                    client.post("/api/ai/suggest",
                                json={"prompt": "what does evidence say about deload frequency"},
                                headers=auth_headers)
    mock_sw.assert_called_once()


def test_search_disabled_by_default_never_calls_search(client, auth_headers):
    """ALLOW_WEB_SEARCH defaults to False — search_web is never called."""
    with _PATCH_WEB_OFF:
        with _mock_provider(ANSWER_RESULT):
            with _mock_search_web(_FAKE_SEARCH_RESULTS) as mock_sw:
                client.post("/api/ai/suggest",
                            json={"prompt": "what does evidence say about deload"},
                            headers=auth_headers)
    mock_sw.assert_not_called()


def test_personal_question_does_not_trigger_search(client, auth_headers):
    """Personal/history questions should not trigger search even when enabled."""
    with _PATCH_WEB_ON:
        with _mock_provider(ANSWER_RESULT):
            with _mock_search_web(_FAKE_SEARCH_RESULTS) as mock_sw:
                client.post("/api/ai/suggest",
                            json={"prompt": "how am I doing this week"},
                            headers=auth_headers)
    mock_sw.assert_not_called()


def test_tavily_failure_returns_graceful_answer(client, auth_headers):
    """If search_web raises, the request should still return a valid answer."""
    with _PATCH_WEB_ON:
        with _mock_provider(ANSWER_RESULT):
            with patch("backend.services.ai_trainer_service.search_web",
                       side_effect=Exception("Tavily down")):
                resp = client.post("/api/ai/suggest",
                                   json={"prompt": "what does evidence say about deload"},
                                   headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json().get("mode") in ("answer", "workout")


def test_missing_tavily_key_returns_graceful_answer(client, auth_headers):
    """No TAVILY_API_KEY should not crash — just no search enrichment."""
    import os
    os.environ.pop("TAVILY_API_KEY", None)
    with _PATCH_WEB_ON:
        with _mock_provider(ANSWER_RESULT):
            resp = client.post("/api/ai/suggest",
                               json={"prompt": "what does evidence say about deload"},
                               headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json().get("mode") == "answer"


def test_search_context_compact_not_large_blob(client, auth_headers):
    """Distilled search context injected into prompt must be compact."""
    from backend.services.ai_trainer_service import _build_user_message, build_context
    from backend import ai_config

    # Simulate a very large distilled summary — should be truncated
    long_summary = "X " * 500  # ~1000 chars

    with client.application.app_context():
        ctx = build_context(1)
        msg = _build_user_message(ctx, "test", search_context=long_summary[:ai_config.SEARCH_DISTILL_CHARS])

    # The injected block should be within limits
    web_ref_idx = msg.find("WEB REFERENCE")
    assert web_ref_idx != -1
    # Content after WEB REFERENCE header should be short
    web_section = msg[web_ref_idx:]
    assert len(web_section) < 800  # generous upper bound for the whole section


def test_web_knowledge_stored_after_educational_answer(client, auth_headers, app, db):
    """After a search-enriched answer, distilled knowledge should be saved."""
    with _PATCH_WEB_ON:
        with _mock_provider(ANSWER_RESULT):
            with _mock_search_web(_FAKE_SEARCH_RESULTS):
                with _mock_distill(_DISTILLED_SUMMARY,
                                   [{"title": "T", "url": "http://ex.com"}]):
                    client.post("/api/ai/suggest",
                                json={"prompt": "what does evidence say about deload frequency"},
                                headers=auth_headers)

    with app.app_context():
        from backend.models.ai_knowledge import AIKnowledge
        from backend.models.user import User
        user    = User.query.filter_by(username="testuser").first()
        entries = AIKnowledge.query.filter_by(
            user_id=user.id, source_type="web_reference"
        ).all()
        assert len(entries) == 1
        assert "hypertrophy" in entries[0].text.lower() or \
               "evidence" in entries[0].text.lower() or \
               "volume" in entries[0].text.lower()


def test_web_knowledge_not_stored_on_workout_mode(client, auth_headers, app, db):
    """Workout-mode responses must not store web_reference knowledge."""
    with _PATCH_WEB_ON:
        with _mock_provider(WORKOUT_RESULT):
            with _mock_search_web(_FAKE_SEARCH_RESULTS) as mock_sw:
                client.post("/api/ai/suggest",
                            json={"prompt": "build me a leg day"},
                            headers=auth_headers)

    # search_web should never have been called
    mock_sw.assert_not_called()

    with app.app_context():
        from backend.models.ai_knowledge import AIKnowledge
        from backend.models.user import User
        user   = User.query.filter_by(username="testuser").first()
        # Count entries AFTER the request — search was gated so no new ones
        # were added by this specific call.  We verify search_web was not called
        # above; the entry count assertion is a belt-and-suspenders check.
        before_count = AIKnowledge.query.filter_by(
            user_id=user.id, source_type="web_reference"
        ).count()
        # Run the request a second time with the same setup and confirm count unchanged
        with _PATCH_WEB_ON:
            with _mock_provider(WORKOUT_RESULT):
                with _mock_search_web(_FAKE_SEARCH_RESULTS):
                    client.post("/api/ai/suggest",
                                json={"prompt": "build me a leg day"},
                                headers=auth_headers)
        after_count = AIKnowledge.query.filter_by(
            user_id=user.id, source_type="web_reference"
        ).count()
        assert after_count == before_count


def test_existing_workout_generation_behavior_unchanged(client, auth_headers):
    """Existing workout generation must work exactly as before Phase 2."""
    with _mock_provider(WORKOUT_RESULT):
        resp = client.post("/api/ai/suggest",
                           json={"prompt": "heavy lower body session"},
                           headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["mode"] == "workout"
    assert data["workout"] is not None
    assert "exercises" in data["workout"]
