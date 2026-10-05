"""
CareerLens — Documents Database Module
=========================================
Auto-saves career portfolio documents (certificates, offer letters, etc.)
"""

import logging
from backend.database.connection import get_db, row_to_dict, resolve_id

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {
    "Resume", "Cover Letter", "Certificate",
    "Offer Letter", "Project", "Reference", "Other"
}


def save_document(user_id: int, name: str, category: str,
                  filename: str, file_size: int = None,
                  file_type: str = None, description: str = None) -> int:
    user_id = resolve_id(user_id)
    if category not in VALID_CATEGORIES:
        category = "Other"

    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO documents
               (user_id, name, category, filename, file_size, file_type, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, name, category, filename, file_size, file_type, description)
        )
        conn.commit()
        logger.info(f"Document saved: id={cur.lastrowid} user_id={user_id} name='{name}'")
        return cur.lastrowid
    finally:
        conn.close()


def get_user_documents(user_id: int) -> list[dict]:
    user_id = resolve_id(user_id)
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id, name, category, filename, file_size,
                      file_type, description, uploaded_at
               FROM documents WHERE user_id = ?
               ORDER BY uploaded_at DESC""",
            (user_id,)
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def delete_document(document_id: int, user_id: int) -> bool:
    document_id = resolve_id(document_id)
    user_id = resolve_id(user_id)
    conn = get_db()
    try:
        result = conn.execute(
            "DELETE FROM documents WHERE id = ? AND user_id = ?",
            (document_id, user_id)
        )
        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()
