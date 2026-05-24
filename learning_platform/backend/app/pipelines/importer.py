from __future__ import annotations

from pathlib import Path

from app.db import get_connection
from app.models import ImportResult
from app.pipelines.segmenter import segment_markdown


PROJECT_ROOT = Path(__file__).resolve().parents[4]
TRACKED_SAMPLE_MARKDOWN = (
    PROJECT_ROOT
    / "learning_platform"
    / "sample_data"
    / "calculus_ii_chapter5_mineru.md"
)
LOCAL_MINERU_MARKDOWN = (
    PROJECT_ROOT
    / "mineru_tools"
    / "output"
    / "20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing"
    / "merged_full.md"
)
SAMPLE_MARKDOWN = TRACKED_SAMPLE_MARKDOWN if TRACKED_SAMPLE_MARKDOWN.exists() else LOCAL_MINERU_MARKDOWN


def import_sample() -> ImportResult:
    """Import the prepared MinerU Markdown into the demo knowledge base.

    This deliberately reads the existing MinerU output instead of re-parsing the PDF,
    so the public-knowledge-base demo is stable without network or API tokens.
    """
    if not SAMPLE_MARKDOWN.exists():
        return ImportResult(ok=False, message=f"找不到样例 Markdown: {SAMPLE_MARKDOWN}")

    markdown = SAMPLE_MARKDOWN.read_text(encoding="utf-8")
    points = segment_markdown(markdown)

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM courses WHERE name = ?",
            ("微积分 II（第四版）",),
        ).fetchone()
        if existing:
            course_id = int(existing["id"])
            chapter = conn.execute(
                "SELECT id FROM chapters WHERE course_id = ? AND title = ?",
                (course_id, "第 5 章 多元函数微分学"),
            ).fetchone()
            chapter_id = int(chapter["id"]) if chapter else None
            kp_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM knowledge_points kp
                JOIN chapters c ON c.id = kp.chapter_id
                WHERE c.course_id = ?
                """,
                (course_id,),
            ).fetchone()["count"]
            unit_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM content_units cu
                JOIN knowledge_points kp ON kp.id = cu.knowledge_point_id
                JOIN chapters c ON c.id = kp.chapter_id
                WHERE c.course_id = ?
                """,
                (course_id,),
            ).fetchone()["count"]
            return ImportResult(
                ok=True,
                message="样例知识库已经导入，无需重复写入。",
                course_id=course_id,
                chapter_id=chapter_id,
                knowledge_points=kp_count,
                content_units=unit_count,
            )

        cursor = conn.execute(
            """
            INSERT INTO courses (name, description, source)
            VALUES (?, ?, ?)
            """,
            (
                "微积分 II（第四版）",
                "由 MinerU 解析结果构建的公共教材知识库样例。",
                str(SAMPLE_MARKDOWN),
            ),
        )
        course_id = int(cursor.lastrowid)
        cursor = conn.execute(
            """
            INSERT INTO chapters (course_id, title, order_index)
            VALUES (?, ?, ?)
            """,
            (course_id, "第 5 章 多元函数微分学", 5),
        )
        chapter_id = int(cursor.lastrowid)

        unit_count = 0
        for order, point in enumerate(points, start=1):
            kp_cursor = conn.execute(
                """
                INSERT INTO knowledge_points
                    (chapter_id, code, title, summary, raw_markdown, order_index, difficulty, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chapter_id,
                    point.code,
                    point.title,
                    point.summary,
                    point.raw_markdown,
                    order,
                    point.difficulty,
                    ",".join(point.tags),
                ),
            )
            kp_id = int(kp_cursor.lastrowid)
            for unit_order, unit in enumerate(point.units, start=1):
                conn.execute(
                    """
                    INSERT INTO content_units
                        (knowledge_point_id, unit_type, title, content, order_index, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (kp_id, unit.unit_type, unit.title, unit.content, unit_order, "MinerU Markdown"),
                )
                unit_count += 1

    return ImportResult(
        ok=True,
        message="已从 MinerU Markdown 导入第 5 章 5.1-5.2 样例知识库。",
        course_id=course_id,
        chapter_id=chapter_id,
        knowledge_points=len(points),
        content_units=unit_count,
    )
