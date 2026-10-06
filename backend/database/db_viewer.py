#!/usr/bin/env python3
"""
CareerLens — Database Viewer
==============================
Run this script to inspect all saved user data in the database.

Usage:
    python3 backend/database/db_viewer.py
    python3 backend/database/db_viewer.py --table users
    python3 backend/database/db_viewer.py --table resumes
    python3 backend/database/db_viewer.py --table interviews
    python3 backend/database/db_viewer.py --user 1
    python3 backend/database/db_viewer.py --stats

Tables:
    users               → accounts (name, email, profile)
    resumes             → uploaded PDFs (text, word count)
    ats_analyses        → ATS audit results
    role_analyses       → career role match results
    learning_roadmaps   → AI-generated roadmaps
    mock_interviews     → interview sessions
    interview_questions → questions + answers + feedback
    chat_history        → AI chatbot conversations
    documents           → portfolio documents
"""

import sys
import os
import json
import argparse

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database.connection import get_db, DB_PATH


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_table(rows: list[dict], hide_cols: list = None):
    if not rows:
        print("  (no records)")
        return
    hide_cols = hide_cols or []
    keys = [k for k in rows[0].keys() if k not in hide_cols]
    for row in rows:
        for k in keys:
            val = row.get(k, "")
            if isinstance(val, str) and len(val) > 80:
                val = val[:77] + "..."
            print(f"    {k:<22}: {val}")
        print("    " + "-"*50)


def show_stats(conn):
    print_header("DATABASE STATISTICS")
    tables = [
        "users", "resumes", "ats_analyses", "role_analyses",
        "learning_roadmaps", "mock_interviews", "interview_questions",
        "chat_history", "documents"
    ]
    print(f"\n  DB Path: {DB_PATH}\n")
    for table in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table:<28}: {count:>5} records")
        except Exception as e:
            print(f"  {table:<28}: ERROR - {e}")


def show_users(conn):
    print_header("USERS")
    rows = conn.execute(
        """SELECT id, name, email, username, phone, job_title,
                  experience_years, created_at
           FROM users ORDER BY id"""
    ).fetchall()
    print_table([dict(r) for r in rows])


def show_resumes(conn):
    print_header("RESUMES")
    rows = conn.execute(
        """SELECT r.id, u.email, r.original_name, r.word_count,
                  r.file_size, r.is_active, r.uploaded_at
           FROM resumes r LEFT JOIN users u ON r.user_id = u.id
           ORDER BY r.uploaded_at DESC LIMIT 20"""
    ).fetchall()
    print_table([dict(r) for r in rows])


def show_ats(conn):
    print_header("ATS ANALYSES")
    rows = conn.execute(
        """SELECT a.id, u.email, a.score, a.rating, a.word_count, a.created_at
           FROM ats_analyses a LEFT JOIN users u ON a.user_id = u.id
           ORDER BY a.created_at DESC LIMIT 20"""
    ).fetchall()
    print_table([dict(r) for r in rows])


def show_roles(conn):
    print_header("ROLE ANALYSES")
    rows = conn.execute(
        """SELECT ra.id, u.email, ra.role, ra.match_score, ra.created_at
           FROM role_analyses ra LEFT JOIN users u ON ra.user_id = u.id
           ORDER BY ra.created_at DESC LIMIT 20"""
    ).fetchall()
    print_table([dict(r) for r in rows])


def show_interviews(conn):
    print_header("MOCK INTERVIEWS")
    rows = conn.execute(
        """SELECT mi.id, u.email, mi.company, mi.role,
                  mi.status, mi.score, mi.created_at
           FROM mock_interviews mi LEFT JOIN users u ON mi.user_id = u.id
           ORDER BY mi.created_at DESC LIMIT 20"""
    ).fetchall()
    print_table([dict(r) for r in rows])
    # Also show questions
    print_header("INTERVIEW QUESTIONS (last 20)")
    rows = conn.execute(
        """SELECT iq.id, mi.company, mi.role, iq.category,
                  iq.question, iq.answer, iq.feedback, iq.answered_at
           FROM interview_questions iq
           JOIN mock_interviews mi ON iq.interview_id = mi.id
           ORDER BY iq.id DESC LIMIT 20"""
    ).fetchall()
    print_table([dict(r) for r in rows])


def show_chat(conn):
    print_header("CHAT HISTORY (last 30)")
    rows = conn.execute(
        """SELECT ch.id, u.email, ch.role, ch.content, ch.created_at
           FROM chat_history ch LEFT JOIN users u ON ch.user_id = u.id
           ORDER BY ch.created_at DESC LIMIT 30"""
    ).fetchall()
    print_table([dict(r) for r in rows])


def show_user_data(conn, user_id: int):
    """Show all data for a specific user."""
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        print(f"  No user found with id={user_id}")
        return
    user = dict(user)
    user.pop("password_hash", None)

    print_header(f"USER #{user_id} — {user.get('name')} ({user.get('email')})")
    for k, v in user.items():
        print(f"  {k:<22}: {v}")

    print_header(f"RESUMES for user #{user_id}")
    rows = conn.execute(
        "SELECT id, original_name, word_count, file_size, is_active, uploaded_at FROM resumes WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    print_table([dict(r) for r in rows])

    print_header(f"ATS ANALYSES for user #{user_id}")
    rows = conn.execute(
        "SELECT id, score, rating, word_count, created_at FROM ats_analyses WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    print_table([dict(r) for r in rows])

    print_header(f"ROLE ANALYSES for user #{user_id}")
    rows = conn.execute(
        "SELECT id, role, match_score, created_at FROM role_analyses WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    print_table([dict(r) for r in rows])

    print_header(f"INTERVIEWS for user #{user_id}")
    rows = conn.execute(
        "SELECT id, company, role, status, score, created_at FROM mock_interviews WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    print_table([dict(r) for r in rows])

    print_header(f"CHAT HISTORY for user #{user_id} (last 10)")
    rows = conn.execute(
        "SELECT role, content, created_at FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
        (user_id,)
    ).fetchall()
    print_table([dict(r) for r in rows])


def main():
    parser = argparse.ArgumentParser(description="CareerLens DB Viewer")
    parser.add_argument("--table", choices=[
        "users", "resumes", "ats", "roles", "interviews", "chat", "stats"
    ], help="Show specific table")
    parser.add_argument("--user", type=int, help="Show all data for a specific user ID")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    args = parser.parse_args()

    print(f"\n🗄️  CareerLens Database Viewer")
    print(f"   DB: {DB_PATH}")

    conn = get_db()

    if args.user:
        show_user_data(conn, args.user)
    elif args.stats or args.table == "stats":
        show_stats(conn)
    elif args.table == "users":
        show_users(conn)
    elif args.table == "resumes":
        show_resumes(conn)
    elif args.table == "ats":
        show_ats(conn)
    elif args.table == "roles":
        show_roles(conn)
    elif args.table == "interviews":
        show_interviews(conn)
    elif args.table == "chat":
        show_chat(conn)
    else:
        # Show everything
        show_stats(conn)
        show_users(conn)
        show_resumes(conn)
        show_ats(conn)
        show_roles(conn)
        show_interviews(conn)
        show_chat(conn)

    conn.close()
    print("\n✅ Done.\n")


if __name__ == "__main__":
    main()
