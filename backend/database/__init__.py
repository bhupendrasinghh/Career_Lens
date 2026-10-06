"""
CareerLens — Backend Database Package
======================================
Organized database layer split by domain:

  backend/database/
  ├── __init__.py          ← re-exports everything (drop-in for old database.py)
  ├── connection.py        ← DB connection, init, migrations
  ├── users.py             ← user accounts, passwords, profiles
  ├── resumes.py           ← resume uploads + raw text
  ├── analyses.py          ← ATS, role analyses, learning roadmaps
  ├── interviews.py        ← mock interview sessions + Q&A
  ├── chat.py              ← AI chatbot history
  └── documents.py         ← career portfolio uploads

All data is auto-saved to SQLite at:
  - Local:      career_lens_website/data/careerlens.db
  - Production: /app/data/careerlens.db  (Render persistent disk)

Usage (same as original database.py — zero breaking changes):
  from backend.database import init_db, get_db, save_resume_to_db, ...
"""

from backend.database.connection import get_db, init_db, row_to_dict, DB_PATH
from backend.database.users import (
    create_user,
    get_user_by_email,
    get_user_by_identifier,
    get_user_by_id,
    update_user_profile,
    update_user_password,
    verify_password,
    hash_password,
)
from backend.database.resumes import (
    save_resume_to_db,
    get_active_resume,
    get_all_resumes,
)
from backend.database.analyses import (
    save_ats_analysis,
    save_role_analysis,
    save_roadmap,
    get_user_history,
)
from backend.database.interviews import (
    create_interview_session,
    save_interview_question,
    get_interview_session,
    get_user_interviews,
    complete_interview,
)
from backend.database.chat import save_chat_message, get_chat_history, clear_chat_history
from backend.database.documents import save_document, get_user_documents, delete_document

__all__ = [
    # Connection
    "get_db", "init_db", "row_to_dict", "DB_PATH",
    # Users
    "create_user", "get_user_by_email", "get_user_by_identifier", "get_user_by_id",
    "update_user_profile", "update_user_password", "verify_password", "hash_password",
    # Resumes
    "save_resume_to_db", "get_active_resume", "get_all_resumes",
    # Analyses
    "save_ats_analysis", "save_role_analysis", "save_roadmap", "get_user_history",
    # Interviews
    "create_interview_session", "save_interview_question",
    "get_interview_session", "get_user_interviews", "complete_interview",
    # Chat
    "save_chat_message", "get_chat_history", "clear_chat_history",
    # Documents
    "save_document", "get_user_documents", "delete_document",
]
