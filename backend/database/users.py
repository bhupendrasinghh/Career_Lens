"""
CareerLens — Users Database Module
====================================
Auto-saves: name, email, hashed password, phone, bio, location,
            job title, experience, GitHub URL, LinkedIn URL, avatar.

Passwords are ALWAYS stored as SHA-256 hash with random salt.
Plain-text passwords are NEVER stored.
"""

import hashlib
import secrets
import logging
from backend.database.connection import get_db, row_to_dict

logger = logging.getLogger(__name__)


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str, salt: str = None) -> str:
    """Return a salted SHA-256 hash in the format  salt:hash."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Return True if provided_password matches the stored hash."""
    try:
        salt, _ = stored_hash.split(":", 1)
        return stored_hash == hash_password(provided_password, salt)
    except Exception:
        return False


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_user(name: str, email: str, password: str) -> dict:
    """
    Create a new user account.
    Password is hashed before storage — plain text never written to DB.
    Returns the created user dict (without password_hash).
    Raises ValueError if email already exists.
    """
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        if existing:
            raise ValueError("An account with this email already exists.")

        ph = hash_password(password)
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email.strip().lower(), ph)
        )
        conn.commit()
        user = row_to_dict(conn.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (cur.lastrowid,)
        ).fetchone())
        logger.info(f"New user created: id={user['id']} email={user['email']}")
        return user
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    """Fetch a user by email (includes password_hash for login verification)."""
    conn = get_db()
    try:
        return row_to_dict(conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone())
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user by ID (never returns password_hash)."""
    conn = get_db()
    try:
        user = row_to_dict(conn.execute(
            """SELECT id, name, email, phone, bio, location, job_title,
                      experience_years, github_url, linkedin_url,
                      avatar_url, created_at, updated_at
               FROM users WHERE id = ?""",
            (user_id,)
        ).fetchone())
        return user
    finally:
        conn.close()


def update_user_profile(user_id: int, updates: dict) -> dict:
    """
    Update allowed profile fields for a user.
    Returns the updated user dict.
    """
    allowed_fields = {
        "name", "phone", "bio", "location",
        "job_title", "experience_years",
        "github_url", "linkedin_url", "avatar_url"
    }
    safe = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}
    if not safe:
        raise ValueError("No valid fields to update.")

    safe["updated_at"] = "datetime('now')"
    set_clause = ", ".join(
        f"{k} = {v}" if k == "updated_at" else f"{k} = ?"
        for k in safe
    )
    values = [v for k, v in safe.items() if k != "updated_at"] + [user_id]

    conn = get_db()
    try:
        conn.execute(
            f"UPDATE users SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        logger.info(f"Profile updated: user_id={user_id} fields={list(safe.keys())}")
        return get_user_by_id(user_id)
    finally:
        conn.close()


def update_user_password(user_id: int, new_password: str) -> bool:
    """
    Update the password hash for a user.
    Plain-text password is hashed before writing.
    Returns True on success.
    """
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
            (hash_password(new_password), user_id)
        )
        conn.commit()
        logger.info(f"Password changed: user_id={user_id}")
        return True
    finally:
        conn.close()
