"""Integration tests — template CRUD, start-from-template, save-as-template."""
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _lib_id(app, name):
    with app.app_context():
        from backend.models.exercise_library import ExerciseLibrary
        return ExerciseLibrary.query.filter_by(name=name).first().id


def _template(client, headers, app, name="Test Template", with_exercises=True):
    payload = {"name": name}
    if with_exercises:
        payload["exercises"] = [{
            "exercise_id": _lib_id(app, "Back Squat"),
            "notes": "deep squat",
            "sets": [
                {"set_type": "working", "reps": 5, "weight": 225, "percent": None},
                {"set_type": "working", "reps": 5, "weight": 225, "percent": None},
                {"set_type": "working", "reps": 5, "weight": 225, "percent": None},
            ],
        }]
    return client.post("/api/templates/", json=payload, headers=headers)


def _other_headers(client, suffix):
    client.post("/api/users/register", json={
        "username": f"tpl_other{suffix}", "email": f"tpl{suffix}@x.com", "password": "pass123"
    })
    token = client.post("/api/users/login", json={
        "username": f"tpl_other{suffix}", "password": "pass123"
    }).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ── Auth guards ────────────────────────────────────────────────────────────────

def test_list_templates_requires_auth(client):
    assert client.get("/api/templates/").status_code == 401


def test_create_template_requires_auth(client):
    assert client.post("/api/templates/", json={"name": "x"}).status_code == 401


def test_start_template_requires_auth(client):
    assert client.post("/api/templates/1/start", json={}).status_code == 401


# ── Create ─────────────────────────────────────────────────────────────────────

def test_create_template_requires_name(client, auth_headers):
    assert client.post("/api/templates/", json={}, headers=auth_headers).status_code == 400


def test_create_template_returns_201(client, auth_headers, app):
    resp = _template(client, auth_headers, app)
    assert resp.status_code == 201
    assert resp.get_json()["name"] == "Test Template"


def test_create_template_includes_exercises(client, auth_headers, app):
    resp = _template(client, auth_headers, app)
    exs = resp.get_json()["exercises"]
    assert len(exs) == 1
    assert exs[0]["exercise_name"] == "Back Squat"
    assert exs[0]["notes"] == "deep squat"


def test_create_template_includes_sets(client, auth_headers, app):
    resp = _template(client, auth_headers, app)
    sets = resp.get_json()["exercises"][0]["sets"]
    assert len(sets) == 3
    assert all(s["reps"] == 5 for s in sets)
    assert all(s["weight"] == 225 for s in sets)


# ── Read ───────────────────────────────────────────────────────────────────────

def test_get_template_returns_200(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    resp = client.get(f"/api/templates/{tid}", headers=auth_headers)
    assert resp.status_code == 200


def test_get_template_other_user_returns_404(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    other = _other_headers(client, "g1")
    assert client.get(f"/api/templates/{tid}", headers=other).status_code == 404


def test_list_templates_scoped_to_user(client, auth_headers, app):
    _template(client, auth_headers, app, name="My Template")
    other = _other_headers(client, "l1")
    names = [t["name"] for t in client.get("/api/templates/", headers=other).get_json()]
    assert "My Template" not in names


# ── Update ─────────────────────────────────────────────────────────────────────

def test_update_template_name(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    resp = client.put(f"/api/templates/{tid}", json={"name": "Renamed"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Renamed"


def test_update_template_replaces_exercises(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    new_ex_id = _lib_id(app, "Deadlift")
    resp = client.put(f"/api/templates/{tid}", json={
        "exercises": [{"exercise_id": new_ex_id, "sets": []}]
    }, headers=auth_headers)
    exs = resp.get_json()["exercises"]
    assert len(exs) == 1
    assert exs[0]["exercise_name"] == "Deadlift"


def test_update_template_other_user_returns_404(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    other = _other_headers(client, "u1")
    assert client.put(f"/api/templates/{tid}", json={"name": "hacked"}, headers=other).status_code == 404


# ── Delete ─────────────────────────────────────────────────────────────────────

def test_delete_template_returns_200(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    assert client.delete(f"/api/templates/{tid}", headers=auth_headers).status_code == 200


def test_delete_template_removes_record(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    client.delete(f"/api/templates/{tid}", headers=auth_headers)
    assert client.get(f"/api/templates/{tid}", headers=auth_headers).status_code == 404


def test_delete_template_other_user_returns_404(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    other = _other_headers(client, "d1")
    assert client.delete(f"/api/templates/{tid}", headers=other).status_code == 404


# ── Start from template ────────────────────────────────────────────────────────

def test_start_template_returns_201(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    resp = client.post(f"/api/templates/{tid}/start", json={}, headers=auth_headers)
    assert resp.status_code == 201


def test_start_template_creates_planned_workout(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    session = client.post(f"/api/templates/{tid}/start", json={}, headers=auth_headers).get_json()
    assert session["status"] == "planned"


def test_start_template_snapshot_has_exercises(client, auth_headers, app, db):
    tid = _template(client, auth_headers, app).get_json()["id"]
    session = client.post(f"/api/templates/{tid}/start", json={}, headers=auth_headers).get_json()
    with app.app_context():
        from backend.models.exercise import Exercise
        exs = Exercise.query.filter_by(workout_id=session["id"]).all()
        assert len(exs) == 1
        assert exs[0].name == "Back Squat"


def test_start_template_snapshot_has_sets(client, auth_headers, app, db):
    tid = _template(client, auth_headers, app).get_json()["id"]
    session = client.post(f"/api/templates/{tid}/start", json={}, headers=auth_headers).get_json()
    with app.app_context():
        from backend.models.exercise import Exercise
        from backend.models.exercise_set import ExerciseSet
        exs = Exercise.query.filter_by(workout_id=session["id"]).all()
        sets = ExerciseSet.query.filter_by(exercise_id=exs[0].id).all()
        assert len(sets) == 3
        assert all(not s.completed for s in sets)


def test_start_template_is_independent_snapshot(client, auth_headers, app, db):
    """Modifying template after start does not affect the created session."""
    tid = _template(client, auth_headers, app).get_json()["id"]
    session = client.post(f"/api/templates/{tid}/start", json={}, headers=auth_headers).get_json()

    new_ex_id = _lib_id(app, "Deadlift")
    client.put(f"/api/templates/{tid}", json={
        "exercises": [{"exercise_id": new_ex_id, "sets": []}]
    }, headers=auth_headers)

    with app.app_context():
        from backend.models.exercise import Exercise
        exs = Exercise.query.filter_by(workout_id=session["id"]).all()
        # original exercise unchanged
        assert exs[0].name == "Back Squat"


def test_start_template_accepts_date_param(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    session = client.post(f"/api/templates/{tid}/start",
                           json={"date": "2026-05-01T09:00:00"},
                           headers=auth_headers).get_json()
    assert "2026-05-01" in session["date"]


def test_start_other_users_template_returns_404(client, auth_headers, app):
    tid = _template(client, auth_headers, app).get_json()["id"]
    other = _other_headers(client, "s1")
    assert client.post(f"/api/templates/{tid}/start", json={}, headers=other).status_code == 404


# ── Save workout as template ───────────────────────────────────────────────────

def test_save_workout_as_template_returns_201(client, auth_headers, app):
    wid = client.post("/api/workouts/", json={"title": "My W", "date": "2026-03-27T12:00:00"},
                      headers=auth_headers).get_json()["id"]
    lib_id = _lib_id(app, "Back Squat")
    client.post(f"/api/workouts/{wid}/exercises", json={
        "name": "Back Squat", "exercise_library_id": lib_id,
        "sets": [{"set_type": "working", "reps": 5, "weight_lb": 225}],
    }, headers=auth_headers)
    resp = client.post(f"/api/workouts/{wid}/save-as-template",
                       json={"name": "Squat Template"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.get_json()["name"] == "Squat Template"


def test_save_workout_as_template_skips_free_text(client, auth_headers, app, db):
    """Exercises without library_id must be excluded from templates."""
    wid = client.post("/api/workouts/", json={"title": "Mixed W", "date": "2026-03-27T12:00:00"},
                      headers=auth_headers).get_json()["id"]
    lib_id = _lib_id(app, "Bench Press")
    # library exercise
    client.post(f"/api/workouts/{wid}/exercises", json={
        "name": "Bench Press", "exercise_library_id": lib_id,
        "sets": [{"set_type": "working", "reps": 5, "weight_lb": 185}],
    }, headers=auth_headers)
    # free-text exercise (no library_id)
    client.post(f"/api/workouts/{wid}/exercises", json={
        "name": "Band Pull-apart",
        "sets": [{"set_type": "working", "reps": 20}],
    }, headers=auth_headers)

    resp = client.post(f"/api/workouts/{wid}/save-as-template", json={}, headers=auth_headers)
    exs = resp.get_json()["exercises"]
    names = [e["exercise_name"] for e in exs]
    assert "Bench Press" in names
    assert "Band Pull-apart" not in names


def test_save_workout_as_template_uses_workout_title_as_default_name(client, auth_headers, app):
    wid = client.post("/api/workouts/", json={"title": "Auto Named", "date": "2026-03-27T12:00:00"},
                      headers=auth_headers).get_json()["id"]
    resp = client.post(f"/api/workouts/{wid}/save-as-template", json={}, headers=auth_headers)
    assert resp.get_json()["name"] == "Auto Named"
