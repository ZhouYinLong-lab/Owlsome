from __future__ import annotations

import re
from collections import Counter

from app.db import get_connection, row_to_dict, rows_to_dicts
from app.models import (
    ExerciseAttemptCreate,
    ExerciseCreate,
    ExerciseLinkRequest,
    ExerciseRecommendCandidate,
    ExerciseRecommendRequest,
    ExerciseRecommendResponse,
)


def tokenize(text: str) -> list[str]:
    """Small Chinese-friendly tokenizer matching the notes module."""
    words = re.findall(r"[一-鿿]{2,}|[A-Za-z0-9.]+", text.lower())
    stop = {"一个", "可以", "函数", "我们", "这个", "中的", "以及"}
    return [word for word in words if word not in stop]


def score_exercise_against_point(exercise_text: str, point: dict) -> tuple[int, str]:
    exercise_tokens = Counter(tokenize(exercise_text))
    haystack = " ".join(
        [
            str(point["code"]),
            str(point["title"]),
            str(point["summary"]),
            str(point["tags"]),
            str(point.get("raw_markdown", ""))[:1000],
        ]
    )
    point_tokens = Counter(tokenize(haystack))
    overlap = exercise_tokens & point_tokens
    score = sum(overlap.values())
    reason_terms = "、".join(list(overlap.keys())[:6]) or "内容相近"
    return score, f"关键词 {reason_terms} 匹配到 {point['code']} {point['title']}。"


def keyword_recommend(exercise_text: str, top_k: int) -> list[ExerciseRecommendCandidate]:
    with get_connection() as conn:
        points = rows_to_dicts(conn.execute("SELECT * FROM knowledge_points ORDER BY order_index").fetchall())
    if not points:
        return []
    scored = []
    for point in points:
        score, reason = score_exercise_against_point(exercise_text, point)
        scored.append((score, int(point["id"]), str(point["code"]), str(point["title"]), reason))
    scored.sort(reverse=True, key=lambda item: item[0])
    candidates = []
    for score, kp_id, code, title, reason in scored[:top_k]:
        if score <= 0:
            break
        candidates.append(
            ExerciseRecommendCandidate(
                knowledge_point_id=kp_id,
                code=code,
                title=title,
                score=round(float(score), 2),
                reason=reason,
            )
        )
    if not candidates and points:
        first = points[0]
        candidates.append(
            ExerciseRecommendCandidate(
                knowledge_point_id=int(first["id"]),
                code=str(first["code"]),
                title=str(first["title"]),
                score=0.0,
                reason="未找到强关键词匹配，默认推荐第一个知识点供人工审核。",
            )
        )
    return candidates


# ── Public API ───────────────────────────────────────────────────


def create_exercise(payload: ExerciseCreate) -> dict:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO exercises (title, stem, answer, analysis, exercise_type, difficulty, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (payload.title, payload.stem, payload.answer, payload.analysis, payload.exercise_type, payload.difficulty, payload.source),
        )
        row = conn.execute("SELECT * FROM exercises WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row) or {}


def list_exercises() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM exercises ORDER BY id DESC").fetchall()
    return rows_to_dicts(rows)


def get_exercise(exercise_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    return row_to_dict(row)


def recommend_knowledge_points(payload: ExerciseRecommendRequest) -> ExerciseRecommendResponse:
    # Gather exercise text from id or stem
    if payload.exercise_id is not None:
        exercise = get_exercise(payload.exercise_id)
        if not exercise:
            raise ValueError(f"题目 id={payload.exercise_id} 不存在。")
        search_text = f"{exercise.get('title', '')}\n{exercise.get('stem', '')}"
    elif payload.stem:
        search_text = payload.stem
    else:
        raise ValueError("请提供 exercise_id 或 stem。")

    # 1) Try optional retrieval adapter
    try:
        from app.services.retrieval import search_knowledge_points

        match = search_knowledge_points(search_text, top_k=payload.top_k, rerank_top_k=payload.top_k)
        if not match.fallback and match.candidates:
            candidates = [
                ExerciseRecommendCandidate(
                    knowledge_point_id=c.knowledge_point_id,
                    code=c.code,
                    title=c.title,
                    score=c.score,
                    reason=c.reason,
                )
                for c in match.candidates
            ]
            return ExerciseRecommendResponse(
                candidates=candidates,
                provider=match.provider,
                fallback=False,
                reason="retrieval",
            )
    except Exception:
        pass  # fall through to keyword fallback

    # 2) Keyword fallback
    candidates = keyword_recommend(search_text, payload.top_k)
    return ExerciseRecommendResponse(
        candidates=candidates,
        provider="keyword",
        fallback=True,
        reason="关键词规则匹配 fallback（BGE 未启用或不可用）。",
    )


def link_exercise(exercise_id: int, payload: ExerciseLinkRequest) -> dict:
    with get_connection() as conn:
        exercise = conn.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
        if not exercise:
            raise ValueError(f"题目 id={exercise_id} 不存在。")
        point = conn.execute("SELECT * FROM knowledge_points WHERE id = ?", (payload.knowledge_point_id,)).fetchone()
        if not point:
            raise ValueError(f"知识点 id={payload.knowledge_point_id} 不存在。")
        conn.execute(
            """
            INSERT OR IGNORE INTO exercise_knowledge_links
                (exercise_id, knowledge_point_id, confidence, reason, confirmed_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (exercise_id, payload.knowledge_point_id, payload.confidence, payload.reason, "local_admin"),
        )
        conn.execute("UPDATE exercises SET status = 'linked' WHERE id = ?", (exercise_id,))
        row = conn.execute("SELECT * FROM exercise_knowledge_links WHERE exercise_id = ? AND knowledge_point_id = ?",
                          (exercise_id, payload.knowledge_point_id)).fetchone()
    return row_to_dict(row) or {}


def list_exercises_for_knowledge_point(knowledge_point_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT e.*, ekl.confidence AS link_confidence, ekl.reason AS link_reason
            FROM exercises e
            JOIN exercise_knowledge_links ekl ON ekl.exercise_id = e.id AND ekl.knowledge_point_id = ?
            WHERE e.status = 'linked'
            ORDER BY e.id
            """,
            (knowledge_point_id,),
        ).fetchall()
    return rows_to_dicts(rows)


def create_attempt(exercise_id: int, payload: ExerciseAttemptCreate) -> dict:
    with get_connection() as conn:
        exercise = conn.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
        if not exercise:
            raise ValueError(f"题目 id={exercise_id} 不存在。")
        cursor = conn.execute(
            """
            INSERT INTO exercise_attempts (exercise_id, knowledge_point_id, result, note)
            VALUES (?, ?, ?, ?)
            """,
            (exercise_id, payload.knowledge_point_id, payload.result, payload.note),
        )
        row = conn.execute("SELECT * FROM exercise_attempts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row) or {}


def list_mistake_exercises(limit: int = 20) -> list[dict]:
    """Return recent wrong/unsure exercise attempts with exercise and knowledge point details."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                ea.id AS attempt_id,
                ea.exercise_id,
                ea.knowledge_point_id,
                ea.result,
                ea.note,
                ea.created_at AS attempted_at,
                e.title AS exercise_title,
                e.stem AS exercise_stem,
                e.answer AS exercise_answer,
                e.analysis AS exercise_analysis,
                kp.code AS knowledge_point_code,
                kp.title AS knowledge_point_title
            FROM exercise_attempts ea
            JOIN exercises e ON e.id = ea.exercise_id
            LEFT JOIN knowledge_points kp ON kp.id = ea.knowledge_point_id
            WHERE ea.result IN ('wrong', 'unsure')
            ORDER BY ea.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)


def list_weak_knowledge_points(limit: int = 10) -> list[dict]:
    """Aggregate wrong/unsure attempts per knowledge point, ignoring null knowledge_point_id."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                ea.knowledge_point_id,
                kp.code,
                kp.title,
                SUM(CASE WHEN ea.result = 'wrong' THEN 1 ELSE 0 END) AS wrong_count,
                SUM(CASE WHEN ea.result = 'unsure' THEN 1 ELSE 0 END) AS unsure_count,
                COUNT(*) AS total_weak_attempts,
                MAX(ea.created_at) AS latest_attempt_at
            FROM exercise_attempts ea
            JOIN knowledge_points kp ON kp.id = ea.knowledge_point_id
            WHERE ea.result IN ('wrong', 'unsure')
            GROUP BY ea.knowledge_point_id
            ORDER BY total_weak_attempts DESC, latest_attempt_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)
