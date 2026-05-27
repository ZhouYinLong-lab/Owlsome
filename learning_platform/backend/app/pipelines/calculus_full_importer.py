from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from app.db import get_connection, init_db
from app.pipelines.importer import LOCAL_FORMATTED_MARKDOWN, LOCAL_MINERU_MARKDOWN, PROJECT_ROOT
from app.pipelines.segmenter import SegmentedChapter, split_full_textbook


COURSE_NAME = "微积分 II（第四版）"
DEFAULT_REPORT = PROJECT_ROOT / "docs" / "test_records" / "calculus_full_import_report.md"


def resolve_full_textbook_input(path: str | None = None) -> Path:
    if path:
        return Path(path)
    if LOCAL_FORMATTED_MARKDOWN.exists():
        return LOCAL_FORMATTED_MARKDOWN
    return LOCAL_MINERU_MARKDOWN


def unit_counts(chapters: list[SegmentedChapter]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for chapter in chapters:
        for point in chapter.points:
            counts.update(unit.unit_type for unit in point.units)
    return counts


def suspicious_points(chapters: list[SegmentedChapter]) -> list[str]:
    warnings: list[str] = []
    for chapter in chapters:
        for point in chapter.points:
            if len(point.raw_markdown) > 18000:
                warnings.append(f"{point.code} {point.title}: 内容过长，可能需要继续拆分。")
            if len(point.raw_markdown) < 120:
                warnings.append(f"{point.code} {point.title}: 内容过短，可能是目录或空标题。")
            if len(point.units) == 1 and point.units[0].unit_type == "explanation":
                warnings.append(f"{point.code} {point.title}: 未识别到定义/定理/例题/习题 marker。")
    return warnings[:80]


def write_report(path: Path, input_path: Path, chapters: list[SegmentedChapter], imported: bool, via_api: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = unit_counts(chapters)
    total_points = sum(len(chapter.points) for chapter in chapters)
    total_units = sum(sum(len(point.units) for point in chapter.points) for chapter in chapters)
    warning_lines = suspicious_points(chapters)
    lines = [
        "# 微积分 II 全书结构化导入报告",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入文件：`{input_path}`",
        f"- 导入数据库：{'是' if imported else '否，dry-run 仅生成报告'}",
        f"- 执行入口：{'learning_platform API / 管理员系统概览' if via_api else 'CLI 脚本'}",
        f"- 识别章节数：{len(chapters)}",
        f"- 识别知识点数：{total_points}",
        f"- 识别内容单元数：{total_units}",
        "",
        "## 内容单元统计",
        "",
        "| 类型 | 数量 |",
        "|---|---:|",
    ]
    for unit_type in ["explanation", "definition", "theorem", "example", "exercise"]:
        lines.append(f"| {unit_type} | {counts.get(unit_type, 0)} |")

    lines.extend(["", "## 章节统计", "", "| 章节 | 知识点 | 内容单元 | 警告 |", "|---|---:|---:|---|"])
    for chapter in chapters:
        chapter_units = sum(len(point.units) for point in chapter.points)
        warning_text = "；".join(chapter.warnings) if chapter.warnings else ""
        lines.append(f"| {chapter.title} | {len(chapter.points)} | {chapter_units} | {warning_text} |")

    lines.extend(["", "## 抽样知识点", ""])
    sample_points = []
    for chapter in chapters[:3]:
        sample_points.extend(chapter.points[:2])
    for point in sample_points[:8]:
        unit_text = ", ".join(unit.unit_type for unit in point.units[:6])
        lines.append(f"- `{point.code}` {point.title}：{len(point.units)} 个单元；前几个类型：{unit_text}")

    lines.extend(["", "## 异常提示", ""])
    if warning_lines:
        lines.extend(f"- {line}" for line in warning_lines)
    else:
        lines.append("- 未发现明显异常。")

    lines.extend([
        "",
        "## 前端验收记录",
        "",
        "- 管理员系统概览已提供全书 dry-run 与真实导入入口。",
        "- 公共资源库左侧资源树应能按章节展示第 5–10 章。",
        "- 章节可展开/收起，知识点详情页应继续显示教材来源与社区贡献标签。",
        "",
        "## 验收建议",
        "",
        "- 抽查每章首尾知识点，确认标题不是目录残留。",
        "- 抽查公式密集段落，确认 LaTeX 未被破坏。",
        "- 抽查例题和习题 marker，确认分类符合教材语义。",
        "- 本报告只验证结构规则，不等价于数学内容审校。",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def reset_course(course_name: str = COURSE_NAME) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM courses WHERE name = ?", (course_name,))


def existing_course_stats(course_id: int) -> dict:
    with get_connection() as conn:
        counts = {
            row["unit_type"]: row["count"]
            for row in conn.execute(
                """
                SELECT cu.unit_type, COUNT(*) AS count
                FROM content_units cu
                JOIN knowledge_points kp ON kp.id = cu.knowledge_point_id
                JOIN chapters c ON c.id = kp.chapter_id
                WHERE c.course_id = ?
                GROUP BY cu.unit_type
                """,
                (course_id,),
            ).fetchall()
        }
        return {
            "chapters": conn.execute(
                "SELECT COUNT(*) AS count FROM chapters WHERE course_id = ?",
                (course_id,),
            ).fetchone()["count"],
            "knowledge_points": conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM knowledge_points kp
                JOIN chapters c ON c.id = kp.chapter_id
                WHERE c.course_id = ?
                """,
                (course_id,),
            ).fetchone()["count"],
            "content_units": conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM content_units cu
                JOIN knowledge_points kp ON kp.id = cu.knowledge_point_id
                JOIN chapters c ON c.id = kp.chapter_id
                WHERE c.course_id = ?
                """,
                (course_id,),
            ).fetchone()["count"],
            "unit_counts": {key: counts.get(key, 0) for key in ["explanation", "definition", "theorem", "example", "exercise"]},
        }


def import_chapters(input_path: Path, chapters: list[SegmentedChapter], reset: bool) -> dict:
    init_db()
    if reset:
        reset_course(COURSE_NAME)

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM courses WHERE name = ?", (COURSE_NAME,)).fetchone()
        if existing:
            return {"course_id": int(existing["id"]), "created": False}
        cursor = conn.execute(
            """
            INSERT INTO courses (name, description, source)
            VALUES (?, ?, ?)
            """,
            (COURSE_NAME, "由清洗版 Markdown 全书规则切分生成的结构化教材。", str(input_path)),
        )
        course_id = int(cursor.lastrowid)

        for chapter in chapters:
            if not chapter.points:
                continue
            chapter_cursor = conn.execute(
                """
                INSERT INTO chapters (course_id, title, order_index)
                VALUES (?, ?, ?)
                """,
                (course_id, chapter.title, chapter.order_index),
            )
            chapter_id = int(chapter_cursor.lastrowid)
            for point_order, point in enumerate(chapter.points, start=1):
                point_cursor = conn.execute(
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
                        point_order,
                        point.difficulty,
                        ",".join(point.tags),
                    ),
                )
                point_id = int(point_cursor.lastrowid)
                for unit_order, unit in enumerate(point.units, start=1):
                    conn.execute(
                        """
                        INSERT INTO content_units
                            (knowledge_point_id, unit_type, title, content, order_index, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            point_id,
                            unit.unit_type,
                            unit.title,
                            unit.content,
                            unit_order,
                            "text_archiver cleaned Markdown full textbook",
                        ),
                    )
    return {"course_id": course_id, "created": True}


def import_calculus_full(
    *,
    dry_run: bool = False,
    reset_course_before_import: bool = False,
    write_report_file: bool = True,
    input_path: str | None = None,
    report_path: str | None = None,
    via_api: bool = False,
) -> dict:
    source_path = resolve_full_textbook_input(input_path)
    report = Path(report_path) if report_path else DEFAULT_REPORT
    if not source_path.exists():
        raise ValueError(f"找不到微积分 II Markdown 输入文件: {source_path}")

    markdown = source_path.read_text(encoding="utf-8")
    chapters = split_full_textbook(markdown)
    if not chapters:
        raise ValueError("未识别到可用章节，请先检查 Markdown 标题结构。")

    parsed_counts = unit_counts(chapters)
    parsed_stats = {
        "chapters": len(chapters),
        "knowledge_points": sum(len(chapter.points) for chapter in chapters),
        "content_units": sum(sum(len(point.units) for point in chapter.points) for chapter in chapters),
        "unit_counts": {
            key: parsed_counts.get(key, 0)
            for key in ["explanation", "definition", "theorem", "example", "exercise"]
        },
    }

    imported = False
    course_id: int | None = None
    message = "已完成微积分 II 全书 dry-run，未写入数据库。"
    output_stats = parsed_stats

    if not dry_run:
        result = import_chapters(source_path, chapters, reset=reset_course_before_import)
        course_id = result["course_id"]
        imported = bool(result["created"])
        if imported:
            message = "已导入清洗版微积分 II 全书。"
            output_stats = parsed_stats
        else:
            message = "微积分 II 全书课程已存在，未重复导入；如需重建请使用 reset_course=true。"
            output_stats = existing_course_stats(course_id)

    report_error = ""
    if write_report_file:
        try:
            write_report(report, source_path, chapters, imported=not dry_run, via_api=via_api)
        except OSError as exc:
            # Report generation is useful for demos and audits, but the import
            # result should remain usable if Windows temporarily locks the file.
            report_error = f"报告写入失败：{exc}"

    return {
        "ok": True,
        "message": f"{message} {report_error}".strip(),
        "course_id": course_id,
        "input_path": str(source_path),
        "report_path": "" if report_error or not write_report_file else str(report),
        "imported": imported,
        "reset_course": reset_course_before_import,
        **output_stats,
    }
