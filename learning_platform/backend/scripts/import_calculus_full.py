from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import get_connection, init_db
from app.pipelines.importer import LOCAL_FORMATTED_MARKDOWN, LOCAL_MINERU_MARKDOWN
from app.pipelines.segmenter import SegmentedChapter, split_full_textbook


COURSE_NAME = "微积分 II（第四版）"
DEFAULT_REPORT = Path(__file__).resolve().parents[3] / "docs" / "test_records" / "calculus_full_import_report.md"


def resolve_input(path: str | None) -> Path:
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


def write_report(path: Path, input_path: Path, chapters: list[SegmentedChapter], imported: bool) -> None:
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
        "## 验收建议",
        "",
        "- 抽查每章首尾知识点，确认标题不是目录残留。",
        "- 抽查公式密集段落，确认 LaTeX 未被破坏。",
        "- 抽查例题和习题 marker，确认分类符合教材语义。",
        "- 本报告只验证结构规则，不等价于数学内容审校。",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def reset_course(course_name: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM courses WHERE name = ?", (course_name,))


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


def print_summary(input_path: Path, chapters: list[SegmentedChapter], report_path: Path, imported: bool) -> None:
    counts = unit_counts(chapters)
    total_points = sum(len(chapter.points) for chapter in chapters)
    total_units = sum(sum(len(point.units) for point in chapter.points) for chapter in chapters)
    print("\n微积分 II 全书结构化处理完成")
    print("=" * 52)
    print(f"输入文件: {input_path}")
    print(f"导入数据库: {'是' if imported else '否，dry-run'}")
    print(f"章节数: {len(chapters)}")
    print(f"知识点数: {total_points}")
    print(f"内容单元数: {total_units}")
    print(
        "单元类型: "
        f"讲解 {counts.get('explanation', 0)} / "
        f"定义 {counts.get('definition', 0)} / "
        f"定理 {counts.get('theorem', 0)} / "
        f"例题 {counts.get('example', 0)} / "
        f"习题 {counts.get('exercise', 0)}"
    )
    print(f"报告路径: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the full cleaned Calculus II Markdown with rule-based segmentation.")
    parser.add_argument("--input", help="清洗版或 MinerU Markdown 路径；默认优先 merged_full_formatted.md")
    parser.add_argument("--dry-run", action="store_true", help="只切分并生成报告，不写入数据库")
    parser.add_argument("--import", dest="do_import", action="store_true", help="写入 SQLite 公共知识库")
    parser.add_argument("--reset-course", action="store_true", help="导入前删除同名课程及其下属章节/知识点")
    parser.add_argument("--report", help=f"报告输出路径，默认 {DEFAULT_REPORT}")
    args = parser.parse_args()

    input_path = resolve_input(args.input)
    report_path = Path(args.report) if args.report else DEFAULT_REPORT
    if not input_path.exists():
        raise SystemExit(f"找不到输入文件: {input_path}")

    markdown = input_path.read_text(encoding="utf-8")
    chapters = split_full_textbook(markdown)
    if not chapters:
        raise SystemExit("未识别到可用章节，请先检查 Markdown 标题结构。")

    imported = bool(args.do_import and not args.dry_run)
    if imported:
        import_chapters(input_path, chapters, reset=args.reset_course)
    write_report(report_path, input_path, chapters, imported=imported)
    print_summary(input_path, chapters, report_path, imported=imported)

    if not imported:
        print("\n下一步可执行真实导入:")
        print("python scripts\\import_calculus_full.py --import --reset-course")


if __name__ == "__main__":
    main()
