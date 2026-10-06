"""
CareerLens — Database Compatibility Shim
========================================
This module re-exports the modular database implementation from `backend.database`.
All actual models, tables, and logic live under:
  backend/database/
    ├── connection.py    (DB connection, schema init, safe migrations)
    ├── users.py         (user accounts, credentials, profiles)
    ├── resumes.py       (resume uploads, extracted text)
    ├── analyses.py      (ATS analyses, role skills, learning roadmaps)
    ├── interviews.py    (mock interview sessions & questions)
    ├── chat.py          (AI chatbot conversation history)
    ├── documents.py     (portfolio documents)
    └── db_viewer.py     (CLI inspection tool)

Auto-saved SQLite path:
  data/careerlens.db
"""

from backend.database import (
    DB_PATH,
    get_db,
    init_db,
    row_to_dict,
    # Users
    create_user,
    get_user_by_email,
    get_user_by_identifier,
    get_user_by_id,
    update_user_profile,
    update_user_password,
    verify_password,
    hash_password,
    # Resumes
    save_resume_to_db,
    get_active_resume,
    get_all_resumes,
    # Analyses & Roadmaps
    save_ats_analysis,
    save_role_analysis,
    save_roadmap,
    get_user_history,
    # Interviews
    create_interview_session,
    save_interview_question,
    get_interview_session,
    get_user_interviews,
    complete_interview,
    # Chat & Documents
    save_chat_message,
    get_chat_history,
    clear_chat_history,
    save_document,
    get_user_documents,
    delete_document,
)

__all__ = [
    "DB_PATH",
    "get_db",
    "init_db",
    "row_to_dict",
    "create_user",
    "get_user_by_email",
    "get_user_by_identifier",
    "get_user_by_id",
    "update_user_profile",
    "update_user_password",
    "verify_password",
    "hash_password",
    "save_resume_to_db",
    "get_active_resume",
    "get_all_resumes",
    "save_ats_analysis",
    "save_role_analysis",
    "save_roadmap",
    "get_user_history",
    "create_interview_session",
    "save_interview_question",
    "get_interview_session",
    "get_user_interviews",
    "complete_interview",
    "save_chat_message",
    "get_chat_history",
    "clear_chat_history",
    "save_document",
    "get_user_documents",
    "delete_document",
]
