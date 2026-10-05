"""
CareerLens — Chat History Database Module
==========================================
Auto-saves every AI chatbot message (user + assistant) per user.
Enables conversation continuity across sessions.
"""

import logging
from backend.database.connection import get_db, row_to_dict, resolve_id

logger = logging.getLogger(__name__)


def save_chat_message(user_id: int, role: str, content: str) -> int:
    user_id = resolve_id(user_id)
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_chat_history(user_id: int, limit: int = 50) -> list[dict]:
    user_id = resolve_id(user_id)
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id, role, content, created_at
               FROM chat_history WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit)
        ).fetchall()
        return list(reversed([row_to_dict(r) for r in rows]))
    finally:
        conn.close()


def clear_chat_history(user_id: int) -> int:
    user_id = resolve_id(user_id)
    conn = get_db()
    try:
        result = conn.execute(
            "DELETE FROM chat_history WHERE user_id = ?", (user_id,)
        )
        conn.commit()
        logger.info(f"Chat cleared: user_id={user_id} deleted={result.rowcount}")
        return result.rowcount
    finally:
        conn.close()
