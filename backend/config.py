import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = f"sqlite:///{os.path.join(ROOT_DIR, 'workouts.db')}"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value or value in ("dev-secret", "dev-jwt-secret", "change-me", "change-me-too"):
        import sys
        if os.getenv("FLASK_ENV") != "development":
            print(f"ERROR: {name} must be set to a secure value in production.", file=sys.stderr)
            sys.exit(1)
    return value or f"dev-{name.lower()}"


class Config:
    SECRET_KEY = _require_env("SECRET_KEY")
    JWT_SECRET_KEY = _require_env("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", DEFAULT_DB)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    # Cookie-based JWT
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = os.getenv("FLASK_ENV") != "development"  # HTTPS only in production
    JWT_COOKIE_SAMESITE = "Strict"
    JWT_COOKIE_CSRF_PROTECT = False  # SameSite=Strict prevents cross-origin requests
