from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from backend.db.database import db
from backend.models.user import User

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.post("/register")
def register():
    from flask_bcrypt import Bcrypt
    bcrypt = Bcrypt()

    data = request.get_json()
    if not data or not data.get("username") or not data.get("email") or not data.get("password"):
        return jsonify({"error": "username, email, and password are required"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    password_hash = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(username=data["username"], email=data["email"], password_hash=password_hash)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "token": token}), 201


@users_bp.post("/login")
def login():
    from flask_bcrypt import Bcrypt
    bcrypt = Bcrypt()

    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.to_dict(), "token": token})
