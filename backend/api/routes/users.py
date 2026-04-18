from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, set_access_cookies, unset_jwt_cookies
from backend.db.database import db
from backend.models.user import User
from backend.app import bcrypt, limiter

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.post("/register")
@limiter.limit("5 per minute")
def register():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("email") or not data.get("password"):
        return jsonify({"error": "username, email, and password are required"}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken"}), 409

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    password_hash = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(username=data["username"], email=data["email"], password_hash=password_hash)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    resp = jsonify({"user": user.to_dict()})
    set_access_cookies(resp, token)
    return resp, 201


@users_bp.post("/login")
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "username and password are required"}), 400

    user = User.query.filter_by(username=data["username"]).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id))
    resp = jsonify({"user": user.to_dict()})
    set_access_cookies(resp, token)
    return resp


@users_bp.post("/logout")
@jwt_required()
def logout():
    resp = jsonify({"message": "Logged out"})
    unset_jwt_cookies(resp)
    return resp


@users_bp.get("/me")
@jwt_required()
def get_me():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "Not found"}), 404
    return jsonify(user.to_dict())


@users_bp.patch("/me")
@jwt_required()
def update_me():
    user = User.query.get(int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json() or {}
    if "unit" in data and data["unit"] in ("lb", "kg"):
        user.unit = data["unit"]
    if "timezone" in data:
        try:
            ZoneInfo(data["timezone"])
            user.timezone = data["timezone"]
        except (ZoneInfoNotFoundError, KeyError):
            return jsonify({"error": "Invalid timezone"}), 400
    db.session.commit()
    return jsonify(user.to_dict())
