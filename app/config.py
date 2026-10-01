"""
All settings come from environment variables so the same code runs in
development, in Docker, and on a host like Render/Railway without any
code changes - only the .env file differs. See .env.example.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me")
    DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "career_planner.db"))
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    TESTING = False
