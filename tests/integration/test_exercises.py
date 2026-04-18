"""Integration tests — exercise and set CRUD, ownership enforcement."""
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _workout(client, headers, title="W"):
    return client.post("/api/workouts/", json={"title": title, "date": "2026-03-27T12:00:00"},
                       headers=headers).get_json()["id"]


def _exercise(client, headers, workout_id, name="Bench Press", sets=None):
    payload = {"name": name, "sets": sets or [{"set_type": "working", "reps": 5, "weight_lb": 135}]}
    return client.post(f"/api/workouts/{workout_id}/exercises", json=payload, headers=headers)


def _other_headers(client):
    """Register a second user and return their auth headers."""
    suffix = str(id(client))[-6:]
    client.post("/api/users/register", json={
        "username": f"other{suffix}", "email": f"o{suffix}@x.com", "password": "pass123"
    })
    token = client.post("/api/users/login", json={
        "username": f"other{suffix}", "password": "pass123"
    }).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ── Auth guards ────────────────────────────────────────────────────────────────

def test_create_exercise_requires_auth(client):
    assert client.post("/api/workouts/1/exercises", json={"name": "x"}).status_code == 401


def test_update_exercise_requires_auth(client):
    assert client.put("/api/exercises/1", json={"name": "x"}).status_code == 401


def test_delete_exercise_requires_auth(client):
    assert client.delete("/api/exercises/1").status_code == 401


# ── Create ─────────────────────────────────────────────────────────────────────

def test_create_exercise_requires_name(client, auth_headers):
    wid = _workout(client, auth_headers)
    resp = client.post(f"/api/workouts/{wid}/exercises",
                       json={"sets": []}, headers=auth_headers)
    assert resp.status_code == 400


def test_create_exercise_returns_201(client, auth_headers):
    wid = _workout(client, auth_headers)
    resp = _exercise(client, auth_headers, wid)
    assert resp.status_code == 201
    assert resp.get_json()["name"] == "Bench Press"


def test_create_exercise_with_multiple_set_types(client, auth_headers, app, db):
    wid = _workout(client, auth_headers)
    resp = _exercise(client, auth_headers, wid, sets=[
        {"set_type": "warmup",  "reps": 5, "weight_lb": 95},
        {"set_type": "working", "reps": 5, "weight_lb": 185},
        {"set_type": "amrap",   "reps": None, "weight_lb": 185},
    ])
    assert resp.status_code == 201
    sets = resp.get_json()["sets"]
    assert len(sets) == 3
    types = [s["set_type"] for s in sets]
    assert "warmup" in types
    assert "amrap" in types


def test_create_exercise_sets_include_percent(client, auth_headers):
    wid = _workout(client, auth_headers)
    resp = _exercise(client, auth_headers, wid, sets=[
        {"set_type": "working", "reps": 5, "weight_lb": 225, "percent": 75.0}
    ])
    s = resp.get_json()["sets"][0]
    assert s["percent"] == 75.0
    assert s["weight_lb"] == 225.0


def test_create_exercise_on_nonexistent_workout_returns_404(client, auth_headers):
    resp = client.post("/api/workouts/99999/exercises",
                       json={"name": "Squat"}, headers=auth_headers)
    assert resp.status_code == 404


def test_create_exercise_on_other_users_workout_returns_404(client, auth_headers):
    wid = _workout(client, auth_headers)
    other = _other_headers(client)
    resp = client.post(f"/api/workouts/{wid}/exercises",
                       json={"name": "Squat"}, headers=other)
    assert resp.status_code == 404


# ── List ───────────────────────────────────────────────────────────────────────

def test_list_exercises_returns_all_for_workout(client, auth_headers):
    wid = _workout(client, auth_headers)
    _exercise(client, auth_headers, wid, "Squat")
    _exercise(client, auth_headers, wid, "Deadlift")
    resp = client.get(f"/api/workouts/{wid}/exercises", headers=auth_headers)
    assert resp.status_code == 200
    names = [e["name"] for e in resp.get_json()]
    assert "Squat" in names
    assert "Deadlift" in names


def test_list_exercises_other_users_workout_returns_404(client, auth_headers):
    wid = _workout(client, auth_headers)
    other = _other_headers(client)
    assert client.get(f"/api/workouts/{wid}/exercises", headers=other).status_code == 404


# ── Update (ownership regression) ─────────────────────────────────────────────

def test_update_exercise_name(client, auth_headers):
    wid = _workout(client, auth_headers)
    eid = _exercise(client, auth_headers, wid).get_json()["id"]
    resp = client.put(f"/api/exercises/{eid}", json={"name": "Incline Press"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Incline Press"


def test_update_exercise_other_user_returns_404(client, auth_headers):
    """Security regression: update_exercise had no ownership check."""
    wid = _workout(client, auth_headers)
    eid = _exercise(client, auth_headers, wid).get_json()["id"]
    other = _other_headers(client)
    resp = client.put(f"/api/exercises/{eid}", json={"name": "Hacked"}, headers=other)
    assert resp.status_code == 404


def test_update_exercise_name_not_changed_by_other_user(client, auth_headers, app, db):
    """After ownership-blocked update, data is unchanged."""
    wid = _workout(client, auth_headers)
    eid = _exercise(client, auth_headers, wid, "Original Name").get_json()["id"]
    other = _other_headers(client)
    client.put(f"/api/exercises/{eid}", json={"name": "Tampered"}, headers=other)
    with app.app_context():
        from backend.models.exercise import Exercise
        ex = Exercise.query.get(eid)
        assert ex.name == "Original Name"


# ── Delete (ownership regression) ─────────────────────────────────────────────

def test_delete_exercise_returns_200(client, auth_headers):
    wid = _workout(client, auth_headers)
    eid = _exercise(client, auth_headers, wid).get_json()["id"]
    assert client.delete(f"/api/exercises/{eid}", headers=auth_headers).status_code == 200


def test_delete_exercise_other_user_returns_404(client, auth_headers):
    """Security regression: delete_exercise had no ownership check."""
    wid = _workout(client, auth_headers)
    eid = _exercise(client, auth_headers, wid).get_json()["id"]
    other = _other_headers(client)
    assert client.delete(f"/api/exercises/{eid}", headers=other).status_code == 404


def test_delete_exercise_other_user_does_not_remove_record(client, auth_headers, app, db):
    wid = _workout(client, auth_headers)
    eid = _exercise(client, auth_headers, wid).get_json()["id"]
    other = _other_headers(client)
    client.delete(f"/api/exercises/{eid}", headers=other)
    with app.app_context():
        from backend.models.exercise import Exercise
        assert Exercise.query.get(eid) is not None


# ── Patch set ──────────────────────────────────────────────────────────────────

def test_patch_set_updates_reps(client, auth_headers):
    wid = _workout(client, auth_headers)
    sets = _exercise(client, auth_headers, wid).get_json()["sets"]
    sid = sets[0]["id"]
    resp = client.patch(f"/api/session-sets/{sid}", json={"reps": 8}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["reps"] == 8


def test_patch_set_marks_completed(client, auth_headers):
    wid = _workout(client, auth_headers)
    sets = _exercise(client, auth_headers, wid).get_json()["sets"]
    sid = sets[0]["id"]
    resp = client.patch(f"/api/session-sets/{sid}", json={"completed": False}, headers=auth_headers)
    assert resp.get_json()["completed"] is False


def test_patch_set_other_user_returns_404(client, auth_headers):
    wid = _workout(client, auth_headers)
    sets = _exercise(client, auth_headers, wid).get_json()["sets"]
    sid = sets[0]["id"]
    other = _other_headers(client)
    assert client.patch(f"/api/session-sets/{sid}", json={"reps": 99}, headers=other).status_code == 404


def test_patch_nonexistent_set_returns_404(client, auth_headers):
    assert client.patch("/api/session-sets/99999", json={"reps": 5}, headers=auth_headers).status_code == 404
