"""
CareerLens — Resumes Database Module
======================================
Auto-saves: filename, original PDF name, file size, word count,
            character count, and full extracted text per user.

Every upload is persisted. Only one resume is "active" at a time
(used for re-loading AI analyses when session expires).
"""

import logging
from backend.database.connection import get_db, row_to_dict

logger = logging.getLogger(__name__)


def save_resume_to_db(user_id: int, filename: str, original_name: str,
                      file_size: int, word_count: int, char_count: int,
                      raw_text: str) -> int:
    """
    Persist a resume upload for a user.
    Marks all previous resumes as inactive and returns the new resume's ID.

    Auto-saved data:
      - user_id        → which user owns this resume
      - filename       → stored filename (UUID-based)
      - original_name  → original PDF filename shown to user
      - file_size      → size in bytes
      - word_count     → number of words extracted
      - char_count     → number of characters extracted
      - raw_text       → full plain-text extracted from PDF
      - uploaded_at    → timestamp (auto)
      - is_active      → 1 (marks this as the current resume)
    """
    if isinstance(user_id, dict):
        user_id = user_id.get("id")
    conn = get_db()
    try:
        # Deactivate previous resumes
        conn.execute(
            "UPDATE resumes SET is_active = 0 WHERE user_id = ?", (user_id,)
        )
        cur = conn.execute(
            """INSERT INTO resumes
               (user_id, filename, original_name, file_size,
                word_count, char_count, raw_text, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (user_id, filename, original_name, file_size,
             word_count, char_count, raw_text)
        )
        conn.commit()
        resume_id = cur.lastrowid
        logger.info(
            f"Resume saved: id={resume_id} user_id={user_id} "
            f"name='{original_name}' words={word_count}"
        )
        return resume_id
    finally:
        conn.close()


def get_active_resume(user_id: int) -> dict | None:
    """
    Return the user's current (most recently uploaded) resume.
    Includes raw_text so the AI can re-analyze without re-uploading.
    """
    conn = get_db()
    try:
        row = conn.execute(
            """SELECT * FROM resumes
               WHERE user_id = ? AND is_active = 1
               ORDER BY uploaded_at DESC LIMIT 1""",
            (user_id,)
        ).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def get_all_resumes(user_id: int) -> list[dict]:
    """
    Return all resumes uploaded by a user (without raw_text for efficiency).
    Sorted newest first.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id, original_name, file_size, word_count,
                      char_count, is_active, uploaded_at
               FROM resumes
               WHERE user_id = ?
               ORDER BY uploaded_at DESC""",
            (user_id,)
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()
