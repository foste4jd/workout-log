"""Integration tests — workout CRUD, date handling, copy, multi-workout day."""
import pytest
from datetime import datetime


# ── Helpers ────────────────────────────────────────────────────────────────────

def _create(client, headers, **kwargs):
    payload = {"title": "Test Workout", "date": "2026-03-27T12:00:00", **kwargs}
    return client.post("/api/workouts/", json=payload, headers=headers)


# ── Auth guards ────────────────────────────────────────────────────────────────

def test_list_workouts_requires_auth(client):
    assert client.get("/api/workouts/").status_code == 401


def test_create_workout_requires_auth(client):
    assert client.post("/api/workouts/", json={"title": "x"}).status_code == 401


def test_get_workout_requires_auth(client):
    assert client.get("/api/workouts/999").status_code == 401


# ── Create ─────────────────────────────────────────────────────────────────────

def test_create_workout_requires_title(client, auth_headers):
    resp = client.post("/api/workouts/", json={"date": "2026-03-27"}, headers=auth_headers)
    assert resp.status_code == 400


def test_create_workout_returns_201(client, auth_headers):
    resp = _create(client, auth_headers)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "Test Workout"
    assert "id" in data


def test_create_workout_defaults_completed_status(client, auth_headers):
    resp = _create(client, auth_headers)
    assert resp.get_json()["status"] == "completed"


def test_create_workout_stores_provided_date(client, auth_headers):
    resp = _create(client, auth_headers, date="2026-01-15T10:00:00")
    assert "2026-01-15" in resp.get_json()["date"]


def test_create_workout_stores_notes(client, auth_headers):
    resp = _create(client, auth_headers, notes="felt strong")
    assert resp.get_json()["notes"] == "felt strong"


def test_create_workout_stores_duration(client, auth_headers):
    resp = _create(client, auth_headers, duration_minutes=75)
    assert resp.get_json()["duration_minutes"] == 75


# ── Multiple workouts per day ──────────────────────────────────────────────────

def test_two_workouts_same_day_both_persist(client, auth_headers):
    same_date = "2026-03-27T08:00:00"
    r1 = client.post("/api/workouts/", json={"title": "AM Session", "date": same_date}, headers=auth_headers)
    r2 = client.post("/api/workouts/", json={"title": "PM Session", "date": same_date}, headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.get_json()["id"] != r2.get_json()["id"]


def test_list_returns_all_workouts_for_day(client, auth_headers):
    date = "2026-03-28T12:00:00"
    client.post("/api/workouts/", json={"title": "W1", "date": date}, headers=auth_headers)
    client.post("/api/workouts/", json={"title": "W2", "date": date}, headers=auth_headers)
    resp = client.get("/api/workouts/", headers=auth_headers)
    titles = [w["title"] for w in resp.get_json()]
    assert "W1" in titles
    assert "W2" in titles


# ── Read ───────────────────────────────────────────────────────────────────────

def test_get_workout_returns_200(client, auth_headers):
    wid = _create(client, auth_headers).get_json()["id"]
    resp = client.get(f"/api/workouts/{wid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["id"] == wid


def test_get_workout_not_found_returns_404(client, auth_headers):
    assert client.get("/api/workouts/99999", headers=auth_headers).status_code == 404


def test_list_workouts_scoped_to_user(client, auth_headers, app):
    """A second user cannot see the first user's workouts."""
    _create(client, auth_headers, title="Private Workout")

    # Register second user and get their token
    client.post("/api/users/register", json={
        "username": "otheruser", "email": "other@x.com", "password": "pass123"
    })
    token2 = client.post("/api/users/login", json={
        "username": "otheruser", "password": "pass123"
    }).get_json()["token"]
    other_headers = {"Authorization": f"Bearer {token2}"}

    titles = [w["title"] for w in client.get("/api/workouts/", headers=other_headers).get_json()]
    assert "Private Workout" not in titles


def test_get_other_users_workout_returns_404(client, auth_headers, app):
    wid = _create(client, auth_headers).get_json()["id"]

    client.post("/api/users/register", json={
        "username": "intruder2", "email": "i2@x.com", "password": "pass123"
    })
    token2 = client.post("/api/users/login", json={
        "username": "intruder2", "password": "pass123"
    }).get_json()["token"]
    other_headers = {"Authorization": f"Bearer {token2}"}

    assert client.get(f"/api/workouts/{wid}", headers=other_headers).status_code == 404


# ── Update ─────────────────────────────────────────────────────────────────────

def test_update_workout_title(client, auth_headers):
    wid = _create(client, auth_headers).get_json()["id"]
    resp = client.put(f"/api/workouts/{wid}", json={"title": "Updated"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Updated"


def test_update_workout_date(client, auth_headers):
    wid = _create(client, auth_headers, date="2026-03-01T12:00:00").get_json()["id"]
    resp = client.put(f"/api/workouts/{wid}", json={"date": "2026-04-01T12:00:00"}, headers=auth_headers)
    assert resp.status_code == 200
    assert "2026-04-01" in resp.get_json()["date"]


def test_update_workout_status(client, auth_headers):
    wid = _create(client, auth_headers).get_json()["id"]
    resp = client.put(f"/api/workouts/{wid}", json={"status": "in_progress"}, headers=auth_headers)
    assert resp.get_json()["status"] == "in_progress"


def test_update_other_users_workout_returns_404(client, auth_headers, app):
    wid = _create(client, auth_headers).get_json()["id"]

    client.post("/api/users/register", json={
        "username": "intruder3", "email": "i3@x.com", "password": "pass123"
    })
    token2 = client.post("/api/users/login", json={
        "username": "intruder3", "password": "pass123"
    }).get_json()["token"]
    other_headers = {"Authorization": f"Bearer {token2}"}

    assert client.put(f"/api/workouts/{wid}", json={"title": "hacked"}, headers=other_headers).status_code == 404


# ── Delete ─────────────────────────────────────────────────────────────────────

def test_delete_workout_returns_200(client, auth_headers):
    wid = _create(client, auth_headers).get_json()["id"]
    assert client.delete(f"/api/workouts/{wid}", headers=auth_headers).status_code == 200


def test_delete_workout_removes_record(client, auth_headers):
    wid = _create(client, auth_headers).get_json()["id"]
    client.delete(f"/api/workouts/{wid}", headers=auth_headers)
    assert client.get(f"/api/workouts/{wid}", headers=auth_headers).status_code == 404


def test_delete_other_users_workout_returns_404(client, auth_headers, app):
    wid = _create(client, auth_headers).get_json()["id"]

    client.post("/api/users/register", json={
        "username": "intruder4", "email": "i4@x.com", "password": "pass123"
    })
    token2 = client.post("/api/users/login", json={
        "username": "intruder4", "password": "pass123"
    }).get_json()["token"]
    other_headers = {"Authorization": f"Bearer {token2}"}

    assert client.delete(f"/api/workouts/{wid}", headers=other_headers).status_code == 404


# ── Complete ───────────────────────────────────────────────────────────────────

def test_complete_workout_sets_status(client, auth_headers):
    wid = _create(client, auth_headers).get_json()["id"]
    client.put(f"/api/workouts/{wid}", json={"status": "planned"}, headers=auth_headers)
    resp = client.post(f"/api/workouts/{wid}/complete", json={}, headers=auth_headers)
    assert resp.get_json()["status"] == "completed"


def test_complete_workout_records_duration(client, auth_headers):
    wid = _create(client, auth_headers).get_json()["id"]
    resp = client.post(f"/api/workouts/{wid}/complete",
                       json={"duration_minutes": 55}, headers=auth_headers)
    assert resp.get_json()["duration_minutes"] == 55


# ── Copy workout ───────────────────────────────────────────────────────────────

def test_copy_workout_creates_new_record(client, auth_headers, app, db):
    wid = _create(client, auth_headers).get_json()["id"]
    resp = client.post(f"/api/workouts/{wid}/copy", json={}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.get_json()["id"] != wid


def test_copy_workout_status_is_planned(client, auth_headers):
    wid = _create(client, auth_headers).get_json()["id"]
    resp = client.post(f"/api/workouts/{wid}/copy", json={}, headers=auth_headers)
    assert resp.get_json()["status"] == "planned"


def test_copy_workout_preserves_exercise_notes(client, auth_headers, app, db):
    """Regression: copy_session was dropping exercise notes."""
    wid = _create(client, auth_headers).get_json()["id"]
    client.post(f"/api/workouts/{wid}/exercises", json={
        "name": "Bench Press",
        "notes": "touch and go reps",
        "sets": [{"set_type": "working", "reps": 5, "weight_lb": 185}],
    }, headers=auth_headers)

    copy_id = client.post(f"/api/workouts/{wid}/copy", json={}, headers=auth_headers).get_json()["id"]

    with app.app_context():
        from backend.models.exercise import Exercise
        exercises = Exercise.query.filter_by(workout_id=copy_id).all()
        assert any(e.notes == "touch and go reps" for e in exercises)


def test_copy_workout_preserves_sets(client, auth_headers, app, db):
    wid = _create(client, auth_headers).get_json()["id"]
    client.post(f"/api/workouts/{wid}/exercises", json={
        "name": "Deadlift",
        "sets": [
            {"set_type": "working", "reps": 5, "weight_lb": 315},
            {"set_type": "working", "reps": 5, "weight_lb": 315},
        ],
    }, headers=auth_headers)

    copy_id = client.post(f"/api/workouts/{wid}/copy", json={}, headers=auth_headers).get_json()["id"]

    with app.app_context():
        from backend.models.exercise import Exercise
        from backend.models.exercise_set import ExerciseSet
        exs = Exercise.query.filter_by(workout_id=copy_id).all()
        total = sum(ExerciseSet.query.filter_by(exercise_id=e.id).count() for e in exs)
        assert total == 2
