"""
CareerLens — Database Connection & Schema
==========================================
Handles:
  - SQLite connection with WAL mode + foreign keys
  - Full schema creation (all 8 tables)
  - Safe column migrations (won't crash on existing DBs)
  - DB stored at: data/careerlens.db  (auto-created)
"""

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

# ── DB Path ───────────────────────────────────────────────────────────────────
# Checks env var first (set on Render to /app/data/careerlens.db),
# then falls back to a local  data/  folder next to this file's project root.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_DB   = os.path.join(_PROJECT_ROOT, "data", "careerlens.db")

DB_PATH = os.getenv("DATABASE_PATH", _DEFAULT_DB)

# Auto-create the data directory if it doesn't exist
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)

logger.info(f"CareerLens DB path: {DB_PATH}")


# ── Connection ────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    """Return a thread-safe SQLite connection with row_factory and WAL mode."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Write-Ahead Logging for concurrency
    conn.execute("PRAGMA foreign_keys=ON")     # Enforce FK constraints
    conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety vs speed
    return conn


def row_to_dict(row) -> dict | None:
    """Convert a sqlite3.Row to a plain dict. Returns None if row is None."""
    if row is None:
        return None
    return dict(row)


def resolve_id(val) -> int | None:
    """Extract integer ID from an int, string, or dict containing 'id'."""
    if val is None:
        return None
    if isinstance(val, dict):
        val = val.get("id")
    try:
        return int(val) if val is not None else None
    except (ValueError, TypeError):
        return None


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    """Create all tables + run safe migrations. Called at app startup."""
    conn = get_db()
    c = conn.cursor()

    # ── 1. Users ──────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            email            TEXT    NOT NULL UNIQUE,
            password_hash    TEXT    NOT NULL,
            phone            TEXT,
            bio              TEXT,
            location         TEXT,
            job_title        TEXT,
            experience_years INTEGER DEFAULT 0,
            github_url       TEXT,
            linkedin_url     TEXT,
            avatar_url       TEXT,
            created_at       TEXT    DEFAULT (datetime('now')),
            updated_at       TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── 2. Resumes ────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename      TEXT    NOT NULL,
            original_name TEXT    NOT NULL,
            file_size     INTEGER,
            word_count    INTEGER,
            char_count    INTEGER,
            raw_text      TEXT,
            is_active     INTEGER DEFAULT 1,
            uploaded_at   TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── 3. Documents (portfolio uploads) ──────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name        TEXT    NOT NULL,
            category    TEXT    NOT NULL DEFAULT 'Other',
            filename    TEXT    NOT NULL,
            file_size   INTEGER,
            file_type   TEXT,
            description TEXT,
            uploaded_at TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── 4. ATS Analysis Results ───────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS ats_analyses (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER REFERENCES users(id) ON DELETE SET NULL,
            resume_id        INTEGER REFERENCES resumes(id) ON DELETE SET NULL,
            score            INTEGER,
            rating           TEXT,
            word_count       INTEGER,
            found_sections   TEXT,
            missing_sections TEXT,
            matched_keywords TEXT,
            missing_keywords TEXT,
            suggestions      TEXT,
            breakdown_json   TEXT,
            created_at       TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── 5. Role / Career Analyses ─────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS role_analyses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
            resume_id       INTEGER REFERENCES resumes(id) ON DELETE SET NULL,
            role            TEXT    NOT NULL,
            match_score     INTEGER,
            matched_skills  TEXT,
            missing_skills  TEXT,
            companies       TEXT,
            recommendations TEXT,
            result_json     TEXT,
            created_at      TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── 6. Learning Roadmaps ──────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS learning_roadmaps (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
            resume_id    INTEGER REFERENCES resumes(id) ON DELETE SET NULL,
            target_role  TEXT    NOT NULL,
            roadmap_json TEXT    NOT NULL,
            created_at   TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── 7. Mock Interview Sessions ────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS mock_interviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            company     TEXT    NOT NULL,
            role        TEXT    NOT NULL,
            status      TEXT    DEFAULT 'in_progress',
            score       INTEGER,
            notes       TEXT,
            created_at  TEXT    DEFAULT (datetime('now')),
            completed_at TEXT
        )
    """)

    # ── 8. Interview Questions & Answers ──────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS interview_questions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL REFERENCES mock_interviews(id) ON DELETE CASCADE,
            question     TEXT    NOT NULL,
            category     TEXT    NOT NULL DEFAULT 'General',
            answer       TEXT,
            feedback     TEXT,
            score        INTEGER,
            order_num    INTEGER DEFAULT 0,
            is_pyq       INTEGER DEFAULT 0,
            source_label TEXT    DEFAULT 'AI-Generated Practice Question',
            source_note  TEXT,
            answered_at  TEXT
        )
    """)

    # ── 9. AI Chatbot History ─────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role       TEXT    NOT NULL,
            content    TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── Safe migrations (add new columns to existing databases) ───────────────
    _safe_add_columns(c, "users", [
        ("phone",            "TEXT"),
        ("updated_at",       "TEXT DEFAULT (datetime('now'))"),
        ("avatar_url",       "TEXT"),
    ])
    _safe_add_columns(c, "mock_interviews", [
        ("completed_at",     "TEXT"),
    ])
    _safe_add_columns(c, "interview_questions", [
        ("score",        "INTEGER"),
        ("is_pyq",       "INTEGER DEFAULT 0"),
        ("source_label", "TEXT DEFAULT 'AI-Generated Practice Question'"),
        ("source_note",  "TEXT"),
    ])

    conn.commit()
    conn.close()
    logger.info("✅ CareerLens database schema initialized")


def _safe_add_columns(cursor, table: str, columns: list[tuple]):
    """Add columns to an existing table; silently skip if they already exist."""
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass  # Column already exists — this is expected on upgrades
