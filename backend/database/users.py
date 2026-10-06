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
import re
from werkzeug.security import check_password_hash
from backend.database.connection import get_db, row_to_dict

logger = logging.getLogger(__name__)


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str, salt: str = None) -> str:
    """Return a salted SHA-256 hash in the format salt:hash."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(stored_hash: str, provided_password: str) -> bool:
    """
    Return True if provided_password matches the stored hash.
    Supports salted SHA-256 (with constant-time comparison) and Werkzeug hashes.
    """
    if not stored_hash or not provided_password:
        return False

    # Check Werkzeug hash formats (e.g. pbkdf2:sha256:..., scrypt:...)
    try:
        if stored_hash.startswith(("pbkdf2:", "scrypt:", "argon2:")):
            return check_password_hash(stored_hash, provided_password)
    except Exception:
        pass

    # Check standard salt:sha256 format
    try:
        if ":" in stored_hash:
            salt, hashed = stored_hash.split(":", 1)
            expected = hashlib.sha256((salt + provided_password).encode()).hexdigest()
            return secrets.compare_digest(hashed, expected)
    except Exception:
        pass

    # Fallback check
    try:
        return check_password_hash(stored_hash, provided_password)
    except Exception:
        return False


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_user(name: str, email: str, password: str, username: str = None) -> dict:
    """
    Create a new user account in the central database.
    Password is saved as a secure hash — plain text never written to DB.
    Returns the created user dict (without password_hash).
    Raises ValueError if email or username already exists.
    """
    name = (name or "").strip()
    email = (email or "").strip().lower()

    if not name:
        raise ValueError("Name is required.")
    if not email:
        raise ValueError("Email is required.")
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    if not username:
        prefix = email.split("@")[0] if "@" in email else email
        username = re.sub(r"[^a-zA-Z0-9_.]", "", prefix).lower() or f"user_{secrets.token_hex(4)}"
    else:
        username = username.strip().lower()

    conn = get_db()
    try:
        # Check existing email
        existing_email = conn.execute(
            "SELECT id FROM users WHERE LOWER(email) = ?", (email,)
        ).fetchone()
        if existing_email:
            raise ValueError("An account with this email already exists.")

        # Ensure unique username
        existing_u = conn.execute(
            "SELECT id FROM users WHERE LOWER(username) = ?", (username,)
        ).fetchone()
        if existing_u:
            base_u = username
            c_idx = 1
            while existing_u:
                username = f"{base_u}{c_idx}"
                existing_u = conn.execute(
                    "SELECT id FROM users WHERE LOWER(username) = ?", (username,)
                ).fetchone()
                c_idx += 1

        ph = hash_password(password)
        cur = conn.execute(
            """INSERT INTO users (name, email, username, password_hash, created_at, updated_at)
               VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (name, email, username, ph)
        )
        conn.commit()
        user = row_to_dict(conn.execute(
            "SELECT id, name, email, username, created_at FROM users WHERE id = ?",
            (cur.lastrowid,)
        ).fetchone())
        logger.info(f"New user created: id={user['id']} email={user['email']} username={user.get('username')}")
        return user
    finally:
        conn.close()


def get_user_by_identifier(identifier: str) -> dict | None:
    """
    Fetch a user by email OR username (case-insensitive).
    Includes password_hash for login verification.
    """
    if not identifier:
        return None
    ident = identifier.strip().lower()
    conn = get_db()
    try:
        return row_to_dict(conn.execute(
            """SELECT * FROM users
               WHERE LOWER(email) = ? OR LOWER(username) = ?""",
            (ident, ident)
        ).fetchone())
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    """Fetch a user by email or username (case-insensitive, includes password_hash)."""
    return get_user_by_identifier(email)


def get_user_by_id(user_id: int) -> dict | None:
    """Fetch a user by ID (never returns password_hash)."""
    conn = get_db()
    try:
        user = row_to_dict(conn.execute(
            """SELECT id, name, email, username, phone, bio, location, job_title,
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
