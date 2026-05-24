from __future__ import annotations

from pathlib import Path

from app.db import get_connection, row_to_dict, rows_to_dicts
from app.pipelines.importer import SAMPLE_MARKDOWN
from app.pipelines.segmenter import SegmentedKnowledgePoint, segment_markdown_flexible


MAX_MARKDOWN_BYTES = 2 * 1024 * 1024


def _store_space(title: str, source_file: str, source_type: str, markdown: str) -> dict:
    points = segment_markdown_flexible(markdown)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO personal_spaces (title, source_file, source_type, status)
            VALUES (?, ?, ?, 'ready')
            """,
            (title, source_file, source_type),
        )
        space_id = int(cursor.lastrowid)
        unit_count = _insert_points(conn, space_id, points)
    return {
        "ok": True,
        "message": "已生成个人学习空间。",
        "space_id": space_id,
        "knowledge_points": len(points),
        "content_units": unit_count,
    }


def _insert_points(conn, space_id: int, points: list[SegmentedKnowledgePoint]) -> int:
    unit_count = 0
    for order, point in enumerate(points, start=1):
        cursor = conn.execute(
            """
            INSERT INTO personal_knowledge_points
                (space_id, code, title, summary, raw_markdown, order_index, difficulty, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                space_id,
                point.code,
                point.title,
                point.summary,
                point.raw_markdown,
                order,
                point.difficulty,
                ",".join(point.tags),
            ),
        )
        point_id = int(cursor.lastrowid)
        # Progress is stored separately from content so later user analytics can
        # evolve without mutating the extracted knowledge-point records.
        conn.execute(
            """
            INSERT INTO learning_progress (space_id, personal_knowledge_point_id, status)
            VALUES (?, ?, 'not_started')
            """,
            (space_id, point_id),
        )
        for unit_order, unit in enumerate(point.units, start=1):
            conn.execute(
                """
                INSERT INTO personal_content_units
                    (personal_knowledge_point_id, unit_type, title, content, order_index, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (point_id, unit.unit_type, unit.title, unit.content, unit_order, "personal_upload"),
            )
            unit_count += 1
    return unit_count


def create_space_from_markdown_bytes(filename: str, data: bytes) -> dict:
    if len(data) > MAX_MARKDOWN_BYTES:
        raise ValueError("Markdown 文件超过 2MB，第一版 demo 暂不处理超大文件。")
    try:
        markdown = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("文件不是 UTF-8 文本，请先转成 UTF-8 Markdown。") from exc
    suffix = Path(filename).suffix.lower()
    if suffix not in {".md", ".markdown", ".txt"}:
        raise ValueError("第一版个人空间只接受 .md、.markdown 或 .txt 文件。")
    title = Path(filename).stem or "个人学习资料"
    return _store_space(title, filename, "markdown", markdown)


def create_space_from_sample() -> dict:
    markdown = SAMPLE_MARKDOWN.read_text(encoding="utf-8")
    return _store_space("个人空间：微积分 II 第 5 章样例", str(SAMPLE_MARKDOWN), "sample_markdown", markdown)


def progress_counts(space_id: int) -> dict[str, int]:
    counts = {"not_started": 0, "learning": 0, "mastered": 0, "difficult": 0}
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM learning_progress
            WHERE space_id = ?
            GROUP BY status
            """,
            (space_id,),
        ).fetchall()
    for row in rows:
        counts[row["status"]] = int(row["count"])
    counts["total"] = sum(counts.values())
    return counts


def list_spaces() -> list[dict]:
    with get_connection() as conn:
        spaces = rows_to_dicts(
            conn.execute(
                """
                SELECT ps.*, COUNT(pkp.id) AS knowledge_point_count
                FROM personal_spaces ps
                LEFT JOIN personal_knowledge_points pkp ON pkp.space_id = ps.id
                GROUP BY ps.id
                ORDER BY ps.created_at DESC
                """
            ).fetchall()
        )
    for space in spaces:
        space["progress"] = progress_counts(int(space["id"]))
    return spaces


def get_space(space_id: int) -> dict | None:
    with get_connection() as conn:
        space = row_to_dict(conn.execute("SELECT * FROM personal_spaces WHERE id = ?", (space_id,)).fetchone())
        if not space:
            return None
        points = rows_to_dicts(
            conn.execute(
                """
                SELECT
                    pkp.*,
                    lp.status AS progress_status,
                    COUNT(pcu.id) AS content_count
                FROM personal_knowledge_points pkp
                LEFT JOIN learning_progress lp ON lp.personal_knowledge_point_id = pkp.id
                LEFT JOIN personal_content_units pcu ON pcu.personal_knowledge_point_id = pkp.id
                WHERE pkp.space_id = ?
                GROUP BY pkp.id
                ORDER BY pkp.order_index
                """,
                (space_id,),
            ).fetchall()
        )
    space["points"] = points
    space["progress"] = progress_counts(space_id)
    return space


def get_personal_point(space_id: int, point_id: int) -> dict | None:
    with get_connection() as conn:
        point = row_to_dict(
            conn.execute(
                """
                SELECT pkp.*, lp.status AS progress_status
                FROM personal_knowledge_points pkp
                LEFT JOIN learning_progress lp ON lp.personal_knowledge_point_id = pkp.id
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


def update_progress(space_id: int, point_id: int, status: str) -> dict | None:
    # The four statuses map directly to UI buttons: 未开始、学习中、已掌握、疑难点。
    if status not in {"not_started", "learning", "mastered", "difficult"}:
        raise ValueError("非法进度状态。")
    with get_connection() as conn:
        point = conn.execute(
            "SELECT id FROM personal_knowledge_points WHERE id = ? AND space_id = ?",
            (point_id, space_id),
        ).fetchone()
        if not point:
            return None
        conn.execute(
            """
            INSERT INTO learning_progress (space_id, personal_knowledge_point_id, status, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(space_id, personal_knowledge_point_id)
            DO UPDATE SET status = excluded.status, updated_at = CURRENT_TIMESTAMP
            """,
            (space_id, point_id, status),
        )
    return get_personal_point(space_id, point_id)

