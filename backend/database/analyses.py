"""
CareerLens — Analyses Database Module
=======================================
Auto-saves results of all AI analyses:
  - ATS resume audit scores & breakdown
  - Career role match scores & skill gaps
  - Personalized learning roadmaps
"""

import json
import logging
from backend.database.connection import get_db, row_to_dict, resolve_id

logger = logging.getLogger(__name__)


# ── ATS Analysis ──────────────────────────────────────────────────────────────

def save_ats_analysis(user_id: int, resume_id: int | None, result: dict) -> int:
    user_id = resolve_id(user_id)
    resume_id = resolve_id(resume_id)
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO ats_analyses
               (user_id, resume_id, score, rating, word_count,
                found_sections, missing_sections, matched_keywords,
                missing_keywords, suggestions, breakdown_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, resume_id,
                result.get("score"), result.get("rating"),
                result.get("word_count"),
                json.dumps(result.get("found_sections", [])),
                json.dumps(result.get("missing_sections", [])),
                json.dumps(result.get("matched_keywords", [])),
                json.dumps(result.get("missing_keywords", [])),
                json.dumps(result.get("suggestions", [])),
                json.dumps(result.get("breakdown", {})),
            )
        )
        conn.commit()
        logger.info(
            f"ATS analysis saved: id={cur.lastrowid} user_id={user_id} score={result.get('score')}"
        )
        return cur.lastrowid
    finally:
        conn.close()


# ── Role / Career Analysis ────────────────────────────────────────────────────

def save_role_analysis(user_id: int, resume_id: int | None,
                       role: str, result: dict) -> int:
    user_id = resolve_id(user_id)
    resume_id = resolve_id(resume_id)
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO role_analyses
               (user_id, resume_id, role, match_score,
                matched_skills, missing_skills, result_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, resume_id, role,
                result.get("match_score") or result.get("score"),
                json.dumps(result.get("matched_skills", [])),
                json.dumps(result.get("missing_skills", [])),
                json.dumps(result),
            )
        )
        conn.commit()
        logger.info(
            f"Role analysis saved: id={cur.lastrowid} user_id={user_id} role='{role}'"
        )
        return cur.lastrowid
    finally:
        conn.close()


# ── Learning Roadmap ──────────────────────────────────────────────────────────

def save_roadmap(user_id: int, resume_id: int | None,
                 target_role: str, roadmap: dict) -> int:
    user_id = resolve_id(user_id)
    resume_id = resolve_id(resume_id)
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO learning_roadmaps
               (user_id, resume_id, target_role, roadmap_json)
               VALUES (?, ?, ?, ?)""",
            (user_id, resume_id, target_role, json.dumps(roadmap))
        )
        conn.commit()
        logger.info(
            f"Roadmap saved: id={cur.lastrowid} user_id={user_id} role='{target_role}'"
        )
        return cur.lastrowid
    finally:
        conn.close()


# ── User History ──────────────────────────────────────────────────────────────

def get_user_history(user_id: int) -> dict:
    user_id = resolve_id(user_id)
    conn = get_db()
    try:
        ats = [row_to_dict(r) for r in conn.execute(
            """SELECT id, score, rating, created_at
               FROM ats_analyses WHERE user_id = ?
               ORDER BY created_at DESC LIMIT 10""",
            (user_id,)
        ).fetchall()]

        roles = [row_to_dict(r) for r in conn.execute(
            """SELECT id, role, match_score, created_at
               FROM role_analyses WHERE user_id = ?
               ORDER BY created_at DESC LIMIT 10""",
            (user_id,)
        ).fetchall()]

        roadmaps = [row_to_dict(r) for r in conn.execute(
            """SELECT id, target_role, created_at
               FROM learning_roadmaps WHERE user_id = ?
               ORDER BY created_at DESC LIMIT 10""",
            (user_id,)
        ).fetchall()]

        resumes = [row_to_dict(r) for r in conn.execute(
            """SELECT id, original_name, word_count, uploaded_at, is_active
               FROM resumes WHERE user_id = ?
               ORDER BY uploaded_at DESC LIMIT 5""",
            (user_id,)
        ).fetchall()]

        return {
            "ats_analyses":  ats,
            "role_analyses": roles,
            "roadmaps":      roadmaps,
            "resumes":       resumes,
        }
    finally:
        conn.close()
