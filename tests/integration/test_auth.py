"""Integration tests — registration, login, and auth edge cases."""
import pytest


# ── Registration ───────────────────────────────────────────────────────────────

def test_register_returns_201(client):
    resp = client.post("/api/users/register", json={
        "username": "newuser", "email": "new@x.com", "password": "pass123"
    })
    assert resp.status_code == 201


def test_register_returns_token(client):
    resp = client.post("/api/users/register", json={
        "username": "tokenuser", "email": "token@x.com", "password": "pass123"
    })
    assert "token" in resp.get_json()


def test_register_missing_username_returns_400(client):
    resp = client.post("/api/users/register", json={
        "email": "a@x.com", "password": "pass123"
    })
    assert resp.status_code == 400


def test_register_missing_email_returns_400(client):
    resp = client.post("/api/users/register", json={
        "username": "u", "password": "pass123"
    })
    assert resp.status_code == 400


def test_register_missing_password_returns_400(client):
    resp = client.post("/api/users/register", json={
        "username": "u", "email": "u@x.com"
    })
    assert resp.status_code == 400


def test_register_duplicate_email_returns_409(client):
    client.post("/api/users/register", json={
        "username": "emailuser1", "email": "dup@x.com", "password": "pass123"
    })
    resp = client.post("/api/users/register", json={
        "username": "emailuser2", "email": "dup@x.com", "password": "pass123"
    })
    assert resp.status_code == 409
    assert "Email" in resp.get_json()["error"]


def test_register_duplicate_username_returns_409_not_500(client):
    """Regression: duplicate username hit DB unique constraint -> 500 instead of 409."""
    client.post("/api/users/register", json={
        "username": "dupuser", "email": "first@x.com", "password": "pass123"
    })
    resp = client.post("/api/users/register", json={
        "username": "dupuser", "email": "second@x.com", "password": "pass123"
    })
    assert resp.status_code == 409
    assert resp.get_json().get("error") is not None


def test_register_duplicate_username_error_message_is_meaningful(client):
    client.post("/api/users/register", json={
        "username": "takenuser", "email": "taken@x.com", "password": "pass123"
    })
    resp = client.post("/api/users/register", json={
        "username": "takenuser", "email": "other@x.com", "password": "pass123"
    })
    assert "username" in resp.get_json()["error"].lower() or "taken" in resp.get_json()["error"].lower()


# ── Login ──────────────────────────────────────────────────────────────────────

def test_login_returns_token(client):
    client.post("/api/users/register", json={
        "username": "loginuser", "email": "login@x.com", "password": "pass123"
    })
    resp = client.post("/api/users/login", json={
        "username": "loginuser", "password": "pass123"
    })
    assert resp.status_code == 200
    assert "token" in resp.get_json()


def test_login_wrong_password_returns_401(client):
    client.post("/api/users/register", json={
        "username": "pwduser", "email": "pwd@x.com", "password": "correct"
    })
    resp = client.post("/api/users/login", json={
        "username": "pwduser", "password": "wrong"
    })
    assert resp.status_code == 401


def test_login_unknown_user_returns_401(client):
    resp = client.post("/api/users/login", json={
        "username": "nobody", "password": "pass"
    })
    assert resp.status_code == 401


def test_login_missing_fields_returns_400(client):
    assert client.post("/api/users/login", json={"username": "u"}).status_code == 400
    assert client.post("/api/users/login", json={"password": "p"}).status_code == 400


def test_login_token_grants_access(client):
    """Token returned from login must work for protected endpoints."""
    client.post("/api/users/register", json={
        "username": "accessuser", "email": "access@x.com", "password": "pass123"
    })
    token = client.post("/api/users/login", json={
        "username": "accessuser", "password": "pass123"
    }).get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/workouts/", headers=headers).status_code == 200
