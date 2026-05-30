from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.pipelines.calculus_full_importer import PROJECT_ROOT, resolve_full_textbook_input, unit_counts
from app.pipelines.segmenter import LONG_POINT_THRESHOLD, SegmentedChapter, SegmentedKnowledgePoint, split_full_textbook


DEFAULT_REPORT = PROJECT_ROOT / "docs" / "test_records" / "calculus_content_quality_audit.md"
KNOWN_REVIEW_CODES = {"5.3.2", "6.2.2", "7.7.1", "7.7.3", "7.7.4", "8.1.2", "10.6.4"}


def atomic_write_text(path: Path, text: str) -> None:
    """Write audit reports through a temp file, which is friendlier on Windows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


@dataclass
class AuditIssue:
    severity: str
    category: str
    chapter: str
    code: str
    title: str
    details: str
    recommendation: str


def base_code(code: str) -> str:
    return code.split("-", 1)[0]


def formula_balance_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    block_dollars = text.count("$$")
    if block_dollars % 2:
        warnings.append("`$$` 数量为奇数")

    text_without_blocks = text.replace("$$", "")
    single_dollars = text_without_blocks.count("$")
    if single_dollars % 2:
        warnings.append("行内 `$` 数量为奇数")

    for left, right in [("\\[", "\\]"), ("\\(", "\\)")]:
        if text.count(left) != text.count(right):
            warnings.append(f"`{left}` / `{right}` 数量不一致")
    return warnings


def audit_point(chapter: SegmentedChapter, point: SegmentedKnowledgePoint) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    unit_type_counts = Counter(unit.unit_type for unit in point.units)
    point_base_code = base_code(point.code)

    if len(point.raw_markdown) > LONG_POINT_THRESHOLD:
        issues.append(
            AuditIssue(
                "high",
                "内容过长",
                chapter.title,
                point.code,
                point.title,
                f"raw_markdown 长度 {len(point.raw_markdown)}，超过阈值 {LONG_POINT_THRESHOLD}。",
                "优先人工复核内部稳定标题或编号；无法稳定拆分时保持原文并在演示中避开深跳。",
            )
        )

    if len(point.raw_markdown) < 120:
        issues.append(
            AuditIssue(
                "medium",
                "内容过短",
                chapter.title,
                point.code,
                point.title,
                f"raw_markdown 长度仅 {len(point.raw_markdown)}。",
                "检查是否为目录残留、空标题或 MinerU 分段噪声。",
            )
        )

    if len(point.units) == 1 and point.units[0].unit_type == "explanation":
        issues.append(
            AuditIssue(
                "medium",
                "marker 识别不足",
                chapter.title,
                point.code,
                point.title,
                "仅识别到 1 个 explanation 单元，未命中定义/定理/例题/习题 marker。",
                "人工抽查教材排版；必要时补充 marker 正则或改进 text_archiver 清洗规范。",
            )
        )

    formula_warnings = formula_balance_warnings(point.raw_markdown)
    if formula_warnings:
        issues.append(
            AuditIssue(
                "medium",
                "公式符号疑似不平衡",
                chapter.title,
                point.code,
                point.title,
                "；".join(formula_warnings),
                "抽查前后相邻段落，确认公式没有在 chunk 边界或清洗阶段被截断。",
            )
        )

    if point_base_code in KNOWN_REVIEW_CODES:
        detail = (
            f"长度 {len(point.raw_markdown)}；单元 {len(point.units)}；"
            f"定义 {unit_type_counts.get('definition', 0)} / 定理 {unit_type_counts.get('theorem', 0)} / "
            f"例题 {unit_type_counts.get('example', 0)} / 习题 {unit_type_counts.get('exercise', 0)}。"
        )
        issues.append(
            AuditIssue(
                "review",
                "重点复核项",
                chapter.title,
                point.code,
                point.title,
                detail,
                "这是前序导入报告中的重点项；若已被二次切分，抽查切分边界和公式连续性。",
            )
        )

    return issues


def collect_issues(chapters: list[SegmentedChapter]) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for chapter in chapters:
        for point in chapter.points:
            issues.extend(audit_point(chapter, point))
    severity_order = {"high": 0, "medium": 1, "review": 2}
    return sorted(issues, key=lambda item: (severity_order.get(item.severity, 9), item.chapter, item.code))


def write_audit_report(path: Path, input_path: Path, chapters: list[SegmentedChapter], issues: list[AuditIssue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = unit_counts(chapters)
    total_points = sum(len(chapter.points) for chapter in chapters)
    total_units = sum(sum(len(point.units) for point in chapter.points) for chapter in chapters)
    split_points = [
        (chapter, point)
        for chapter in chapters
        for point in chapter.points
        if "二次切分" in point.tags or "-" in point.code
    ]

    lines = [
        "# 微积分 II 内容质量 QA 报告",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 输入文件：`{input_path}`",
        "- 检查方式：规则切分结果静态 QA，不调用 LLM，不等价于完整数学审校。",
        f"- 长知识点阈值：{LONG_POINT_THRESHOLD} 字符",
        "",
        "## 总览",
        "",
        f"- 章节数：{len(chapters)}",
        f"- 知识点数：{total_points}",
        f"- 内容单元数：{total_units}",
        f"- QA 问题数：{len(issues)}",
        "",
        "| 单元类型 | 数量 |",
        "|---|---:|",
    ]
    for unit_type in ["explanation", "definition", "theorem", "example", "exercise"]:
        lines.append(f"| {unit_type} | {counts.get(unit_type, 0)} |")

    lines.extend(["", "## 章节统计", "", "| 章节 | 知识点 | 内容单元 |", "|---|---:|---:|"])
    for chapter in chapters:
        chapter_units = sum(len(point.units) for point in chapter.points)
        lines.append(f"| {chapter.title} | {len(chapter.points)} | {chapter_units} |")

    lines.extend(["", "## 二次切分结果", ""])
    if split_points:
        lines.extend(["| 章节 | 知识点 | 长度 | 单元数 |", "|---|---|---:|---:|"])
        for chapter, point in split_points:
            lines.append(f"| {chapter.title} | `{point.code}` {point.title} | {len(point.raw_markdown)} | {len(point.units)} |")
    else:
        lines.append("- 未触发自动二次切分。")

    lines.extend(["", "## 待复核问题", ""])
    if issues:
        lines.extend(["| 级别 | 类型 | 章节 | 知识点 | 详情 | 建议 |", "|---|---|---|---|---|---|"])
        for issue in issues:
            lines.append(
                f"| {issue.severity} | {issue.category} | {issue.chapter} | "
                f"`{issue.code}` {issue.title} | {issue.details} | {issue.recommendation} |"
            )
    else:
        lines.append("- 未发现明显结构质量问题。")

    lines.extend(
        [
            "",
            "## 演示验收建议",
            "",
            "- 优先抽查第 5、6、8、10 章中被二次切分或标记复核的知识点。",
            "- 公共资源库演示时可以搜索“隐函数”“换元积分法”“欧拉方程”，确认长内容可快速定位。",
            "- QA 报告发现的问题不阻断 demo，但应作为后续人工审校和规则优化队列。",
        ]
    )
    atomic_write_text(path, "\n".join(lines))


def print_summary(report_path: Path, chapters: list[SegmentedChapter], issues: list[AuditIssue]) -> None:
    total_points = sum(len(chapter.points) for chapter in chapters)
    total_units = sum(sum(len(point.units) for point in chapter.points) for chapter in chapters)
    high_count = sum(1 for issue in issues if issue.severity == "high")
    print("微积分 II 内容质量 QA 完成")
    print("=" * 44)
    print(f"章节数: {len(chapters)}")
    print(f"知识点数: {total_points}")
    print(f"内容单元数: {total_units}")
    print(f"问题数: {len(issues)}，高优先级: {high_count}")
    print(f"报告路径: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit structured Calculus II Markdown import quality.")
    parser.add_argument("--input", help="清洗版或 MinerU Markdown 路径；默认优先 merged_full_formatted.md")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help=f"QA 报告输出路径，默认 {DEFAULT_REPORT}")
    args = parser.parse_args()

    input_path = resolve_full_textbook_input(args.input)
    if not input_path.exists():
        raise SystemExit(f"找不到微积分 II Markdown 输入文件: {input_path}")

    chapters = split_full_textbook(input_path.read_text(encoding="utf-8"))
    if not chapters:
        raise SystemExit("未识别到可用章节，请先检查 Markdown 标题结构。")

    issues = collect_issues(chapters)
    report_path = Path(args.report)
    write_audit_report(report_path, input_path, chapters, issues)
    print_summary(report_path, chapters, issues)


if __name__ == "__main__":
    main()
