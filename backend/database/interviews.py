"""
CareerLens — Interviews Database Module
=========================================
Auto-saves:
  - Mock interview sessions (company, role, status, score)
  - Individual questions with user answers and AI feedback
"""

import logging
from datetime import datetime
from backend.database.connection import get_db, row_to_dict, resolve_id

logger = logging.getLogger(__name__)


def create_interview_session(user_id: int, company: str, role: str) -> int:
    user_id = resolve_id(user_id)
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO mock_interviews (user_id, company, role) VALUES (?, ?, ?)",
            (user_id, company, role)
        )
        conn.commit()
        session_id = cur.lastrowid
        logger.info(
            f"Interview created: id={session_id} user_id={user_id} "
            f"company='{company}' role='{role}'"
        )
        return session_id
    finally:
        conn.close()


def save_interview_question(interview_id: int, question: str,
                            category: str = "General",
                            answer: str = None,
                            feedback: str = None,
                            score: int = None,
                            order_num: int = 0,
                            is_pyq: bool = False,
                            source_label: str = "AI-Generated Practice Question",
                            source_note: str = None) -> int:
    interview_id = resolve_id(interview_id)
    conn = get_db()
    try:
        answered_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") if answer else None
        cur = conn.execute(
            """INSERT INTO interview_questions
               (interview_id, question, category, answer, feedback, score,
                order_num, is_pyq, source_label, source_note, answered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (interview_id, question, category, answer, feedback, score,
             order_num, int(is_pyq), source_label, source_note, answered_at)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_interview_session(interview_id: int) -> dict | None:
    interview_id = resolve_id(interview_id)
    conn = get_db()
    try:
        session = row_to_dict(conn.execute(
            "SELECT * FROM mock_interviews WHERE id = ?", (interview_id,)
        ).fetchone())
        if not session:
            return None
        questions = [row_to_dict(r) for r in conn.execute(
            """SELECT * FROM interview_questions
               WHERE interview_id = ?
               ORDER BY order_num ASC""",
            (interview_id,)
        ).fetchall()]
        session["questions"] = questions
        return session
    finally:
        conn.close()


def get_user_interviews(user_id: int, limit: int = 20) -> list[dict]:
    user_id = resolve_id(user_id)
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id, company, role, status, score, created_at
               FROM mock_interviews WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def complete_interview(interview_id: int, score: int = None, notes: str = None) -> bool:
    interview_id = resolve_id(interview_id)
    conn = get_db()
    try:
        conn.execute(
            """UPDATE mock_interviews
               SET status = 'completed', score = ?, notes = ?,
                   completed_at = datetime('now')
               WHERE id = ?""",
            (score, notes, interview_id)
        )
        conn.commit()
        logger.info(f"Interview completed: id={interview_id} score={score}")
        return True
    finally:
        conn.close()
