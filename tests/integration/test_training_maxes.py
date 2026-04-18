"""Integration tests — training max CRUD and ownership.

Uses a dedicated 'tmuser' rather than 'testuser' to avoid polluting the shared
DB state that unit tests rely on (specifically the Back Squat and Overhead Press
TMs expected to be absent in test_blocks_to_sets_* unit tests).
"""
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _lib_id(app, name):
    with app.app_context():
        from backend.models.exercise_library import ExerciseLibrary
        return ExerciseLibrary.query.filter_by(name=name).first().id


def _upsert(client, headers, exercise_id, weight=300.0, notes=None):
    payload = {"exercise_id": exercise_id, "training_max_weight": weight}
    if notes:
        payload["notes"] = notes
    return client.post("/api/training-maxes/", json=payload, headers=headers)


@pytest.fixture
def tm_headers(client):
    """Dedicated user for TM tests — keeps testuser's TM state clean for unit tests."""
    client.post("/api/users/register", json={
        "username": "tmuser", "email": "tmuser@test.com", "password": "tmpass123"
    })
    token = client.post("/api/users/login", json={
        "username": "tmuser", "password": "tmpass123"
    }).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _other_headers(client, suffix):
    client.post("/api/users/register", json={
        "username": f"tm_other{suffix}", "email": f"tm{suffix}@x.com", "password": "pass123"
    })
    token = client.post("/api/users/login", json={
        "username": f"tm_other{suffix}", "password": "pass123"
    }).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ── Auth guards ────────────────────────────────────────────────────────────────

def test_list_maxes_requires_auth(client):
    assert client.get("/api/training-maxes/").status_code == 401


def test_upsert_max_requires_auth(client):
    assert client.post("/api/training-maxes/", json={"exercise_id": 1, "training_max_weight": 300}).status_code == 401


def test_delete_max_requires_auth(client):
    assert client.delete("/api/training-maxes/1").status_code == 401


# ── Upsert ─────────────────────────────────────────────────────────────────────

def test_upsert_creates_max(client, tm_headers, app):
    eid = _lib_id(app, "Back Squat")
    resp = _upsert(client, tm_headers, eid, weight=315.0)
    assert resp.status_code == 200
    assert resp.get_json()["training_max_weight"] == 315.0


def test_upsert_returns_exercise_name(client, tm_headers, app):
    eid = _lib_id(app, "Deadlift")
    resp = _upsert(client, tm_headers, eid, weight=405.0)
    assert resp.get_json()["exercise_name"] == "Deadlift"


def test_upsert_updates_existing_max(client, tm_headers, app):
    eid = _lib_id(app, "Bench Press")
    _upsert(client, tm_headers, eid, weight=225.0)
    resp = _upsert(client, tm_headers, eid, weight=235.0)
    assert resp.get_json()["training_max_weight"] == 235.0


def test_upsert_does_not_create_duplicate(client, tm_headers, app, db):
    """Two upserts for the same exercise must produce one record, not two."""
    eid = _lib_id(app, "Overhead Press")
    _upsert(client, tm_headers, eid, weight=135.0)
    _upsert(client, tm_headers, eid, weight=145.0)
    with app.app_context():
        from backend.models.training_max import TrainingMax
        from backend.models.user import User
        user = User.query.filter_by(username="tmuser").first()
        count = TrainingMax.query.filter_by(user_id=user.id, exercise_id=eid).count()
        assert count == 1


def test_upsert_nonexistent_exercise_returns_404(client, tm_headers):
    resp = client.post("/api/training-maxes/", json={
        "exercise_id": 99999, "training_max_weight": 300
    }, headers=tm_headers)
    assert resp.status_code == 404


def test_upsert_missing_exercise_id_returns_400(client, tm_headers):
    resp = client.post("/api/training-maxes/", json={"training_max_weight": 300}, headers=tm_headers)
    assert resp.status_code == 400


def test_upsert_missing_weight_returns_400(client, tm_headers, app):
    eid = _lib_id(app, "Back Squat")
    resp = client.post("/api/training-maxes/", json={"exercise_id": eid}, headers=tm_headers)
    assert resp.status_code == 400


def test_upsert_stores_notes(client, tm_headers, app):
    eid = _lib_id(app, "Romanian Deadlift")
    resp = _upsert(client, tm_headers, eid, notes="Competition max")
    assert resp.get_json()["notes"] == "Competition max"


# ── List ───────────────────────────────────────────────────────────────────────

def test_list_maxes_returns_own(client, tm_headers, app):
    eid = _lib_id(app, "Bent Over Row")
    _upsert(client, tm_headers, eid, weight=185.0)
    maxes = client.get("/api/training-maxes/", headers=tm_headers).get_json()
    names = [m["exercise_name"] for m in maxes]
    assert "Bent Over Row" in names


def test_list_maxes_user_scoped(client, tm_headers, app):
    """User A's maxes must not appear in User B's list."""
    eid = _lib_id(app, "Pull-up")
    _upsert(client, tm_headers, eid, weight=275.0)

    other = _other_headers(client, "ls1")
    other_maxes = client.get("/api/training-maxes/", headers=other).get_json()
    names = [m["exercise_name"] for m in other_maxes]
    assert "Pull-up" not in names


def test_list_maxes_empty_for_new_user(client, app):
    client.post("/api/users/register", json={
        "username": "freshuser_tm", "email": "fresh_tm@x.com", "password": "pass123"
    })
    token = client.post("/api/users/login", json={
        "username": "freshuser_tm", "password": "pass123"
    }).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/training-maxes/", headers=headers).get_json() == []


# ── Delete ─────────────────────────────────────────────────────────────────────

def test_delete_max_returns_200(client, tm_headers, app, db):
    eid = _lib_id(app, "Barbell Curl")
    mid = _upsert(client, tm_headers, eid).get_json()["id"]
    assert client.delete(f"/api/training-maxes/{mid}", headers=tm_headers).status_code == 200


def test_delete_max_removes_record(client, tm_headers, app, db):
    eid = _lib_id(app, "Barbell Curl")
    mid = _upsert(client, tm_headers, eid, weight=95.0).get_json()["id"]
    client.delete(f"/api/training-maxes/{mid}", headers=tm_headers)
    with app.app_context():
        from backend.models.training_max import TrainingMax
        assert TrainingMax.query.get(mid) is None


def test_delete_other_users_max_returns_404(client, tm_headers, app):
    eid = _lib_id(app, "Barbell Curl")
    mid = _upsert(client, tm_headers, eid, weight=185.0).get_json()["id"]
    other = _other_headers(client, "dl1")
    assert client.delete(f"/api/training-maxes/{mid}", headers=other).status_code == 404


def test_delete_nonexistent_max_returns_404(client, tm_headers):
    assert client.delete("/api/training-maxes/99999", headers=tm_headers).status_code == 404
