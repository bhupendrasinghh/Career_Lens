"""
Career Lens — Authentication Blueprint
Handles user registration, login, logout, and profile management.
Centralized database authentication without device or browser binding.
"""

from flask import Blueprint, request, jsonify, session
import re
from database import (
    create_user,
    get_user_by_identifier,
    get_user_by_id,
    update_user_profile,
    update_user_password,
    verify_password,
    hash_password,
    get_db,
    row_to_dict,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def is_valid_email(email: str) -> bool:
    """Validate that the email address conforms to standard email format."""
    if not email:
        return False
    email = email.strip().lower()
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email))


def current_user_id():
    return session.get("user_id")


def require_auth():
    """Returns (user_id, error_response) — error_response is None if authenticated."""
    uid = current_user_id()
    if not uid:
        return None, (jsonify(error="Authentication required."), 401)
    return uid, None


# ─── Routes ───────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    username = (data.get("username") or "").strip().lower() or None
    password = data.get("password") or ""

    if not name:
        return jsonify(error="Name is required."), 400
    if not email:
        return jsonify(error="Email is required."), 400
    if not is_valid_email(email):
        return jsonify(error="Please enter a valid email address (e.g. yourname@gmail.com)."), 400
    if len(password) < 8:
        return jsonify(error="Password must be at least 8 characters."), 400

    try:
        user = create_user(name=name, email=email, password=password, username=username)

        # Session-based authentication — independent of device or browser
        session.permanent = True
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["username"] = user.get("username", "")

        return jsonify(
            message="Account created successfully.",
            user={
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "username": user.get("username", ""),
            }
        ), 201

    except ValueError as ve:
        return jsonify(error=str(ve)), 409
    except Exception as e:
        return jsonify(error=f"Registration failed: {e}"), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    # Accept 'email', 'username', 'identifier', or 'login' for flexibility across devices
    identifier = (
        data.get("email") or data.get("username") or data.get("identifier") or data.get("login") or ""
    ).strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify(error="Email/username and password are required."), 400

    # Look up user in central database by email OR username (case-insensitive)
    user = get_user_by_identifier(identifier)

    if not user or not verify_password(user["password_hash"], password):
        return jsonify(error="Invalid email/username or password."), 401

    # Session-based authentication — works from any laptop, PC, or device
    session.permanent = True
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    session["username"] = user.get("username", "")

    return jsonify(
        message="Logged in successfully.",
        user={
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "username": user.get("username", ""),
        }
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(message="Logged out successfully.")


@auth_bp.route("/me", methods=["GET"])
def me():
    uid = current_user_id()
    if not uid:
        return jsonify(authenticated=False, user=None)

    user = get_user_by_id(uid)
    if not user:
        session.clear()
        return jsonify(authenticated=False, user=None)
    user.pop("password_hash", None)
    return jsonify(authenticated=True, user=user)


@auth_bp.route("/profile", methods=["PUT"])
def update_profile():
    uid, err = require_auth()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    allowed = ["name", "bio", "location", "github_url", "linkedin_url",
               "phone", "job_title", "experience_years"]

    updates = {k: v for k, v in data.items() if k in allowed and v is not None}

    if not updates:
        return jsonify(error="No valid fields to update."), 400

    try:
        user = update_user_profile(uid, updates)
        if "name" in updates:
            session["user_name"] = updates["name"]
        return jsonify(message="Profile updated successfully.", user=user)
    except Exception as e:
        return jsonify(error=f"Update failed: {e}"), 400


@auth_bp.route("/password", methods=["PUT"])
def change_password():
    uid, err = require_auth()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    current = data.get("current_password") or ""
    new_pw = data.get("new_password") or ""

    if len(new_pw) < 8:
        return jsonify(error="New password must be at least 8 characters."), 400

    conn = get_db()
    try:
        row = row_to_dict(conn.execute(
            "SELECT password_hash FROM users WHERE id = ?", (uid,)
        ).fetchone())

        if not row or not verify_password(row["password_hash"], current):
            return jsonify(error="Current password is incorrect."), 401

        update_user_password(uid, new_pw)
        return jsonify(message="Password changed successfully.")
    finally:
        conn.close()
