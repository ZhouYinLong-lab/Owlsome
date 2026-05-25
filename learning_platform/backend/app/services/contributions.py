from __future__ import annotations

from app.db import get_connection, row_to_dict, rows_to_dicts
from app.models import ContributionCreateFromPersonalPoint, ContributionReviewRequest
from app.services.notes import find_best_match


TYPE_TO_UNIT = {
    "note": "explanation",
    "explanation": "explanation",
    "mistake": "explanation",
    "example": "example",
    "exercise": "exercise",
    "faq": "explanation",
}


def _local_contributor_id(conn) -> int:
    row = conn.execute("SELECT id FROM contributors WHERE handle = 'local_demo_user'").fetchone()
    if row:
        return int(row["id"])
    cursor = conn.execute(
        "INSERT INTO contributors (handle, display_name) VALUES ('local_demo_user', '本地演示用户')"
    )
    return int(cursor.lastrowid)


def _personal_point_with_units(conn, space_id: int, point_id: int) -> dict | None:
    point = row_to_dict(
        conn.execute(
            """
            SELECT pkp.*, ps.title AS space_title
            FROM personal_knowledge_points pkp
            JOIN personal_spaces ps ON ps.id = pkp.space_id
            WHERE pkp.space_id = ? AND pkp.id = ?
            """,
            (space_id, point_id),
        ).fetchone()
    )
    if not point:
        return None
    point["units"] = rows_to_dicts(
        conn.execute(
            """
            SELECT *
            FROM personal_content_units
            WHERE personal_knowledge_point_id = ?
            ORDER BY order_index
            """,
            (point_id,),
        ).fetchall()
    )
    return point


def _contribution_content(point: dict) -> str:
    if point.get("raw_markdown"):
        return point["raw_markdown"]
    units = point.get("units") or []
    return "\n\n".join(unit["content"] for unit in units if unit.get("content")).strip()


def _duplicate_risk(content: str) -> str:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT title
            FROM content_units
            WHERE instr(?, substr(content, 1, 40)) > 0
               OR instr(content, substr(?, 1, 40)) > 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (content, content),
        ).fetchone()
    if row:
        return f"可能与已有内容“{row['title'] or '教材内容'}”存在重叠，请审核确认。"
    return "未发现明显重复，仍需人工审核。"


def create_from_personal_point(payload: ContributionCreateFromPersonalPoint) -> dict:
    with get_connection() as conn:
        point = _personal_point_with_units(conn, payload.space_id, payload.personal_knowledge_point_id)
        if not point:
            raise ValueError("个人知识点不存在。")
        content = _contribution_content(point)
        if not content:
            raise ValueError("个人知识点内容为空，无法申请贡献。")

        title = payload.title.strip() or point["title"]
        recommended_id, match_reason = find_best_match(f"{title}\n{point['summary']}\n{content[:1200]}")
        contributor_id = _local_contributor_id(conn)
        cursor = conn.execute(
            """
            INSERT INTO contributions
                (
                    contributor_id, source_space_id, source_personal_point_id,
                    recommended_knowledge_point_id, target_knowledge_point_id,
                    contribution_type, title, content_scope, status, match_reason, duplicate_risk
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                contributor_id,
                payload.space_id,
                payload.personal_knowledge_point_id,
                recommended_id,
                recommended_id,
                payload.contribution_type,
                title,
                payload.content_scope,
                match_reason,
                _duplicate_risk(content),
            ),
        )
        contribution_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO contribution_units (contribution_id, unit_type, title, content, order_index)
            VALUES (?, ?, ?, ?, 1)
            """,
            (contribution_id, payload.contribution_type, title, content),
        )
    return get_contribution(contribution_id) or {}


def list_pending() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                c.*,
                kp.code AS recommended_code,
                kp.title AS recommended_title,
                ps.title AS source_space_title,
                pkp.code AS source_point_code,
                pkp.title AS source_point_title,
                co.display_name AS contributor_name,
                (
                    SELECT substr(cu.content, 1, 520)
                    FROM contribution_units cu
                    WHERE cu.contribution_id = c.id
                    ORDER BY cu.order_index
                    LIMIT 1
                ) AS content_preview
            FROM contributions c
            LEFT JOIN knowledge_points kp ON kp.id = c.recommended_knowledge_point_id
            LEFT JOIN personal_spaces ps ON ps.id = c.source_space_id
            LEFT JOIN personal_knowledge_points pkp ON pkp.id = c.source_personal_point_id
            LEFT JOIN contributors co ON co.id = c.contributor_id
            WHERE c.status = 'pending'
            ORDER BY c.created_at DESC
            """
        ).fetchall()
    return rows_to_dicts(rows)


def get_contribution(contribution_id: int) -> dict | None:
    with get_connection() as conn:
        contribution = row_to_dict(
            conn.execute(
                """
                SELECT
                    c.*,
                    kp.code AS recommended_code,
                    kp.title AS recommended_title,
                    ps.title AS source_space_title,
                    pkp.code AS source_point_code,
                    pkp.title AS source_point_title,
                    co.display_name AS contributor_name
                FROM contributions c
                LEFT JOIN knowledge_points kp ON kp.id = c.recommended_knowledge_point_id
                LEFT JOIN personal_spaces ps ON ps.id = c.source_space_id
                LEFT JOIN personal_knowledge_points pkp ON pkp.id = c.source_personal_point_id
                LEFT JOIN contributors co ON co.id = c.contributor_id
                WHERE c.id = ?
                """,
                (contribution_id,),
            ).fetchone()
        )
        if not contribution:
            return None
        contribution["units"] = rows_to_dicts(
            conn.execute(
                "SELECT * FROM contribution_units WHERE contribution_id = ? ORDER BY order_index",
                (contribution_id,),
            ).fetchall()
        )
        contribution["reviews"] = rows_to_dicts(
            conn.execute(
                "SELECT * FROM contribution_reviews WHERE contribution_id = ? ORDER BY created_at DESC",
                (contribution_id,),
            ).fetchall()
        )
    return contribution


def approve(contribution_id: int, payload: ContributionReviewRequest) -> dict | None:
    with get_connection() as conn:
        contribution = conn.execute("SELECT * FROM contributions WHERE id = ?", (contribution_id,)).fetchone()
        if not contribution:
            return None
        if contribution["status"] != "pending":
            raise ValueError("只有 pending 状态的贡献可以审核通过。")
        target_id = payload.target_knowledge_point_id or contribution["target_knowledge_point_id"] or contribution[
            "recommended_knowledge_point_id"
        ]
        if not target_id:
            raise ValueError("缺少目标知识点，无法合并贡献。")
        exists = conn.execute("SELECT id FROM knowledge_points WHERE id = ?", (target_id,)).fetchone()
        if not exists:
            raise ValueError("目标知识点不存在。")
        units = conn.execute(
            "SELECT * FROM contribution_units WHERE contribution_id = ? ORDER BY order_index",
            (contribution_id,),
        ).fetchall()
        for order, unit in enumerate(units, start=1):
            conn.execute(
                """
                INSERT INTO content_units
                    (knowledge_point_id, unit_type, title, content, order_index, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    target_id,
                    TYPE_TO_UNIT.get(unit["unit_type"], "explanation"),
                    unit["title"],
                    unit["content"],
                    1000 + order,
                    f"community_contribution:{contribution_id}",
                ),
            )
        conn.execute(
            """
            UPDATE contributions
            SET status = 'approved',
                target_knowledge_point_id = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (target_id, contribution_id),
        )
        conn.execute(
            """
            INSERT INTO contribution_reviews (contribution_id, action, comment)
            VALUES (?, 'approved', ?)
            """,
            (contribution_id, payload.comment),
        )
    return get_contribution(contribution_id)


def reject(contribution_id: int, payload: ContributionReviewRequest) -> dict | None:
    return _review_without_merge(contribution_id, "rejected", payload.comment)


def request_revision(contribution_id: int, payload: ContributionReviewRequest) -> dict | None:
    return _review_without_merge(contribution_id, "needs_revision", payload.comment)


def _review_without_merge(contribution_id: int, status: str, comment: str) -> dict | None:
    with get_connection() as conn:
        contribution = conn.execute("SELECT * FROM contributions WHERE id = ?", (contribution_id,)).fetchone()
        if not contribution:
            return None
        if contribution["status"] != "pending":
            raise ValueError("只有 pending 状态的贡献可以审核。")
        conn.execute(
            "UPDATE contributions SET status = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, contribution_id),
        )
        conn.execute(
            """
            INSERT INTO contribution_reviews (contribution_id, action, comment)
            VALUES (?, ?, ?)
            """,
            (contribution_id, status, comment),
        )
    return get_contribution(contribution_id)
