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
            username         TEXT    UNIQUE,
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
        ("username",         "TEXT"),
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

    # ── Indexes for fast, case-insensitive lookups ───────────────────────────
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users (LOWER(email))")
    except Exception:
        pass

    # ── Backfill username for any existing accounts missing one ───────────────
    _backfill_usernames(c)

    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower ON users (LOWER(username)) WHERE username IS NOT NULL")
    except Exception:
        pass

    conn.commit()

    # ── Migrate legacy database if root careerlens.db exists ──────────────────
    _migrate_legacy_db(conn)

    conn.close()
    logger.info("✅ CareerLens database schema initialized")


def _safe_add_columns(cursor, table: str, columns: list[tuple]):
    """Add columns to an existing table; silently skip if they already exist."""
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass  # Column already exists — this is expected on upgrades


def _backfill_usernames(cursor):
    """Populate unique usernames from email prefixes for any users without one."""
    import re
    try:
        cursor.execute("SELECT id, email, name FROM users WHERE username IS NULL OR username = ''")
        rows = cursor.fetchall()
        for row in rows:
            uid = row["id"]
            email = row["email"] or ""
            prefix = email.split("@")[0].lower() if "@" in email else email.lower()
            clean_prefix = re.sub(r"[^a-zA-Z0-9_.]", "", prefix) or f"user{uid}"
            candidate = clean_prefix
            counter = 1
            while True:
                exists = cursor.execute(
                    "SELECT id FROM users WHERE LOWER(username) = ? AND id != ?",
                    (candidate.lower(), uid)
                ).fetchone()
                if not exists:
                    break
                candidate = f"{clean_prefix}{counter}"
                counter += 1
            cursor.execute("UPDATE users SET username = ? WHERE id = ?", (candidate, uid))
    except Exception as e:
        logger.warning(f"Username backfill skipped: {e}")


def _migrate_legacy_db(current_conn):
    """
    Safely import accounts and historical records from root careerlens.db into the canonical DB.
    Ensures that credentials registered on previous versions or other devices are fully preserved.
    """
    root_db = os.path.join(_PROJECT_ROOT, "careerlens.db")
    canonical_path = os.path.abspath(DB_PATH)
    if not os.path.exists(root_db) or os.path.abspath(root_db) == canonical_path:
        return

    try:
        legacy_conn = sqlite3.connect(root_db)
        legacy_conn.row_factory = sqlite3.Row
        cur = current_conn.cursor()

        # 1. Migrate Users
        legacy_users = legacy_conn.execute("SELECT * FROM users").fetchall()
        user_id_map = {}  # old_user_id -> new_user_id

        for u in legacy_users:
            email = (u["email"] or "").strip().lower()
            existing = cur.execute(
                "SELECT id FROM users WHERE LOWER(email) = ?", (email,)
            ).fetchone()

            if existing:
                user_id_map[u["id"]] = existing[0]
            else:
                prefix = email.split("@")[0] if "@" in email else email
                import re
                candidate_user = re.sub(r"[^a-zA-Z0-9_.]", "", prefix).lower() or f"user_{u['id']}"
                c_idx = 1
                base_u = candidate_user
                while cur.execute("SELECT id FROM users WHERE LOWER(username) = ?", (candidate_user,)).fetchone():
                    candidate_user = f"{base_u}{c_idx}"
                    c_idx += 1

                res = cur.execute(
                    """INSERT INTO users (name, email, username, password_hash, phone, bio, location,
                                          job_title, experience_years, github_url, linkedin_url,
                                          avatar_url, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        u["name"], email, candidate_user, u["password_hash"],
                        u["phone"] if "phone" in u.keys() else None,
                        u["bio"] if "bio" in u.keys() else None,
                        u["location"] if "location" in u.keys() else None,
                        u["job_title"] if "job_title" in u.keys() else None,
                        u["experience_years"] if "experience_years" in u.keys() else 0,
                        u["github_url"] if "github_url" in u.keys() else None,
                        u["linkedin_url"] if "linkedin_url" in u.keys() else None,
                        u["avatar_url"] if "avatar_url" in u.keys() else None,
                        u["created_at"] if "created_at" in u.keys() else "datetime('now')",
                        u["updated_at"] if "updated_at" in u.keys() else "datetime('now')"
                    )
                )
                user_id_map[u["id"]] = res.lastrowid
                logger.info(f"Migrated legacy user: {email} -> new id {res.lastrowid}")

        # 2. Migrate Mock Interviews & Questions
        interview_id_map = {}
        try:
            legacy_interviews = [dict(r) for r in legacy_conn.execute("SELECT * FROM mock_interviews").fetchall()]
            for iv in legacy_interviews:
                new_uid = user_id_map.get(iv["user_id"])
                if not new_uid:
                    continue
                exists = cur.execute(
                    """SELECT id FROM mock_interviews
                       WHERE user_id = ? AND company = ? AND role = ? AND created_at = ?""",
                    (new_uid, iv["company"], iv["role"], iv["created_at"])
                ).fetchone()
                if exists:
                    interview_id_map[iv["id"]] = exists[0]
                else:
                    res = cur.execute(
                        """INSERT INTO mock_interviews (user_id, company, role, status, score, notes, created_at, completed_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (new_uid, iv["company"], iv["role"], iv.get("status", "in_progress"),
                         iv.get("score"), iv.get("notes"), iv.get("created_at"), iv.get("completed_at"))
                    )
                    interview_id_map[iv["id"]] = res.lastrowid

            # Interview questions
            legacy_questions = [dict(r) for r in legacy_conn.execute("SELECT * FROM interview_questions").fetchall()]
            for q in legacy_questions:
                new_ivid = interview_id_map.get(q["interview_id"])
                if not new_ivid:
                    continue
                exists = cur.execute(
                    """SELECT id FROM interview_questions WHERE interview_id = ? AND question = ?""",
                    (new_ivid, q["question"])
                ).fetchone()
                if not exists:
                    cur.execute(
                        """INSERT INTO interview_questions
                           (interview_id, question, category, answer, feedback, score, order_num, is_pyq, source_label, source_note, answered_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (new_ivid, q["question"], q.get("category", "General"), q.get("answer"),
                         q.get("feedback"), q.get("score"), q.get("order_num", 0), q.get("is_pyq", 0),
                         q.get("source_label", "AI-Generated Practice Question"), q.get("source_note"), q.get("answered_at"))
                    )
        except Exception as e:
            logger.warning(f"Legacy interview migration notice: {e}")

        # 3. Migrate Chat History
        try:
            legacy_chats = [dict(r) for r in legacy_conn.execute("SELECT * FROM chat_history").fetchall()]
            for ch in legacy_chats:
                new_uid = user_id_map.get(ch["user_id"])
                if not new_uid:
                    continue
                exists = cur.execute(
                    """SELECT id FROM chat_history WHERE user_id = ? AND content = ? AND created_at = ?""",
                    (new_uid, ch["content"], ch["created_at"])
                ).fetchone()
                if not exists:
                    cur.execute(
                        """INSERT INTO chat_history (user_id, role, content, created_at)
                           VALUES (?, ?, ?, ?)""",
                        (new_uid, ch["role"], ch["content"], ch["created_at"])
                    )
        except Exception as e:
            logger.warning(f"Legacy chat migration notice: {e}")

        # 4. Migrate Documents
        try:
            legacy_docs = [dict(r) for r in legacy_conn.execute("SELECT * FROM documents").fetchall()]
            for d in legacy_docs:
                new_uid = user_id_map.get(d["user_id"])
                if not new_uid:
                    continue
                exists = cur.execute(
                    """SELECT id FROM documents WHERE user_id = ? AND filename = ?""",
                    (new_uid, d["filename"])
                ).fetchone()
                if not exists:
                    cur.execute(
                        """INSERT INTO documents (user_id, name, category, filename, file_size, file_type, description, uploaded_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (new_uid, d["name"], d.get("category", "Other"), d["filename"],
                         d.get("file_size"), d.get("file_type"), d.get("description"), d.get("uploaded_at"))
                    )
        except Exception as e:
            logger.warning(f"Legacy documents migration notice: {e}")

        current_conn.commit()
        legacy_conn.close()
        logger.info("✅ Legacy database migration completed successfully.")
    except Exception as e:
        logger.warning(f"Legacy migration skipped or error: {e}")
