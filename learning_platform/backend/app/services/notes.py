from __future__ import annotations

import re
from collections import Counter

from app.db import get_connection, row_to_dict, rows_to_dicts
from app.models import NoteCreate


def tokenize(text: str) -> list[str]:
    """A small Chinese-friendly matcher for the demo note routing workflow."""
    words = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9.]+", text.lower())
    stop = {"一个", "可以", "函数", "我们", "这个", "中的", "以及"}
    return [word for word in words if word not in stop]


def score_note_against_point(note_text: str, point: dict) -> tuple[int, str]:
    note_tokens = Counter(tokenize(note_text))
    haystack = " ".join([point["code"], point["title"], point["summary"], point["tags"], point["raw_markdown"][:1000]])
    point_tokens = Counter(tokenize(haystack))
    overlap = note_tokens & point_tokens
    score = sum(overlap.values())
    reason_terms = "、".join(list(overlap.keys())[:6]) or "内容相近"
    return score, f"根据关键词 {reason_terms} 自动匹配到 {point['code']} {point['title']}。"


def find_best_match(note_text: str) -> tuple[int | None, str]:
    with get_connection() as conn:
        points = rows_to_dicts(conn.execute("SELECT * FROM knowledge_points ORDER BY order_index").fetchall())
    if not points:
        return None, "知识库为空，请先导入样例。"

    scored = []
    for point in points:
        score, reason = score_note_against_point(note_text, point)
        scored.append((score, int(point["id"]), reason))
    scored.sort(reverse=True, key=lambda item: item[0])
    best_score, best_id, reason = scored[0]
    if best_score <= 0:
        return int(points[0]["id"]), "未找到强关键词匹配，默认进入第一个知识点供人工审核。"
    return best_id, reason


def create_note(payload: NoteCreate) -> dict:
    # 如果用户没有显式指定知识点，就用轻量关键词匹配生成待审核建议。
    matched_id, reason = (
        (payload.knowledge_point_id, "用户手动选择知识点。")
        if payload.knowledge_point_id
        else find_best_match(f"{payload.title}\n{payload.content}")
    )
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO notes
                (knowledge_point_id, matched_knowledge_point_id, title, content, note_type, status, match_reason)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (None, matched_id, payload.title, payload.content, payload.note_type, reason),
        )
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row) or {}


def pending_notes() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT n.*, kp.code AS matched_code, kp.title AS matched_title
            FROM notes n
            LEFT JOIN knowledge_points kp ON kp.id = n.matched_knowledge_point_id
            WHERE n.status = 'pending'
            ORDER BY n.created_at DESC
            """
        ).fetchall()
    return rows_to_dicts(rows)


def approve_note(note_id: int) -> dict | None:
    """Approve a note and merge it into the matched knowledge point.

    The merge is represented by setting knowledge_point_id. The original pending
    record is preserved as provenance, which keeps the audit trail visible.
    """
    with get_connection() as conn:
        note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not note:
            return None
        matched_id = note["matched_knowledge_point_id"]
        conn.execute(
            """
            UPDATE notes
            SET status = 'approved',
                knowledge_point_id = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (matched_id, note_id),
        )
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    return row_to_dict(row)


def reject_note(note_id: int) -> dict | None:
    with get_connection() as conn:
        note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not note:
            return None
        conn.execute(
            "UPDATE notes SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (note_id,),
        )
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    return row_to_dict(row)

