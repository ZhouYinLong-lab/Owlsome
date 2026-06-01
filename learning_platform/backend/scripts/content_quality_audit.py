from __future__ import annotations

import argparse
import re
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
TRACKED_SAMPLE_MARKDOWN = PROJECT_ROOT / "learning_platform" / "sample_data" / "calculus_ii_chapter5_mineru.md"
FORMULA_TITLE_TOKENS = [r"\frac", r"\begin", r"\left", r"\right", r"\sum", r"\int", r"\lim", r"\neq", "^", "_"]
POINT_TITLE_MAX_CHARS = 80
UNIT_TITLE_MAX_CHARS = 100
UNIT_MIN_NONSPACE_CHARS = 20
UNIT_MAX_CHARS = 5000

TITLE_ISSUE_CATEGORIES = {"标题疑似公式", "标题过长"}
LATEX_ISSUE_CATEGORIES = {"LaTeX 分隔符异常", "疑似错误 token"}
MARKER_ISSUE_CATEGORIES = {"marker 识别不足", "marker 类型疑似误识别"}


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
    location: str = ""
    snippet: str = ""

    @property
    def display_location(self) -> str:
        return self.location or self.chapter


def base_code(code: str) -> str:
    return code.split("-", 1)[0]


def resolve_audit_input(path: str | None = None) -> Path:
    if path:
        return Path(path)
    source = resolve_full_textbook_input()
    if source.exists():
        return source
    if TRACKED_SAMPLE_MARKDOWN.exists():
        return TRACKED_SAMPLE_MARKDOWN
    return source


def markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>").strip()


def compact_text(text: str, limit: int = 120) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit - 1]}…"


def snippet_around(text: str, start: int, end: int | None = None, radius: int = 80) -> str:
    end = start + 1 if end is None else end
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(text) else ""
    return compact_text(f"{prefix}{text[left:right]}{suffix}", 180)


def first_token_snippet(text: str, tokens: list[str]) -> str:
    positions = [text.find(token) for token in tokens if token in text]
    positions = [position for position in positions if position >= 0]
    if not positions:
        return compact_text(text, 180)
    return snippet_around(text, min(positions))


def title_formula_tokens(title: str) -> list[str]:
    return [token for token in FORMULA_TITLE_TOKENS if token in title]


def audit_title_text(
    *,
    chapter: str,
    code: str,
    title: str,
    location: str,
    title_kind: str,
    max_chars: int,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    tokens = title_formula_tokens(title)
    if tokens:
        issues.append(
            AuditIssue(
                "warning",
                "标题疑似公式",
                chapter,
                code,
                title,
                f"{title_kind}标题包含疑似 LaTeX token：{', '.join(tokens)}。",
                "人工确认是否为公式误入标题；本 QA 只记录问题，不自动改写教材内容。",
                location=location,
                snippet=first_token_snippet(title, tokens),
            )
        )

    if len(title) > max_chars:
        issues.append(
            AuditIssue(
                "warning",
                "标题过长",
                chapter,
                code,
                title,
                f"{title_kind}标题长度 {len(title)}，超过阈值 {max_chars}。",
                "检查标题是否吞入正文、公式或例题题干；确认后再决定是否调整切分规则。",
                location=location,
                snippet=compact_text(title, 180),
            )
        )
    return issues


def begin_end_warnings(text: str) -> list[tuple[str, str]]:
    warnings: list[tuple[str, str]] = []
    begin_envs = re.findall(r"\\begin\{([^}]+)\}", text)
    end_envs = re.findall(r"\\end\{([^}]+)\}", text)
    if Counter(begin_envs) != Counter(end_envs):
        env_names = sorted(set(begin_envs) | set(end_envs))
        details = []
        for env in env_names:
            begin_count = begin_envs.count(env)
            end_count = end_envs.count(env)
            if begin_count != end_count:
                details.append(f"{env}: begin={begin_count}, end={end_count}")
        match = re.search(r"\\(?:begin|end)\{[^}]+\}", text)
        snippet = snippet_around(text, match.start(), match.end()) if match else compact_text(text, 180)
        warnings.append(("`\\begin{...}` 和 `\\end{...}` 数量不匹配：" + "；".join(details), snippet))
    return warnings


def latex_delimiter_warnings(text: str) -> list[tuple[str, str]]:
    warnings: list[tuple[str, str]] = []
    block_dollars = text.count("$$")
    if block_dollars % 2:
        index = text.find("$$")
        warnings.append(("`$$` 数量为奇数。", snippet_around(text, index, index + 2) if index >= 0 else compact_text(text, 180)))

    text_without_blocks = text.replace("$$", "")
    single_matches = list(re.finditer(r"(?<!\\)\$", text_without_blocks))
    if len(single_matches) % 2:
        match = single_matches[0]
        warnings.append(("行内 `$` 数量为奇数。", snippet_around(text_without_blocks, match.start(), match.end())))

    for left, right in [("\\[", "\\]"), ("\\(", "\\)")]:
        if text.count(left) != text.count(right):
            index = text.find(left)
            if index < 0:
                index = text.find(right)
            warnings.append((f"`{left}` / `{right}` 数量不一致。", snippet_around(text, index, index + 2) if index >= 0 else compact_text(text, 180)))

    warnings.extend(begin_end_warnings(text))
    return warnings


def suspicious_token_warnings(text: str) -> list[tuple[str, str]]:
    checks = [
        ("疑似 `\\en` 残留。", re.compile(r"\\en\b")),
        ("疑似转义下划线 `\\_` 残留。", re.compile(r"\\_")),
        ("疑似多余反斜杠。", re.compile(r"\\(?=$|[\u4e00-\u9fff，。；：、！？）】》])")),
        ("疑似连续异常空格。", re.compile(r"[ \t]{6,}")),
    ]
    warnings: list[tuple[str, str]] = []
    for message, pattern in checks:
        match = pattern.search(text)
        if match:
            warnings.append((message, snippet_around(text, match.start(), match.end())))
    return warnings


def audit_latex_text(
    *,
    chapter: str,
    code: str,
    title: str,
    location: str,
    text: str,
    text_kind: str,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for message, snippet in latex_delimiter_warnings(text):
        issues.append(
            AuditIssue(
                "warning",
                "LaTeX 分隔符异常",
                chapter,
                code,
                title,
                f"{text_kind}：{message}",
                "抽查可疑片段附近的公式边界，确认是否被清洗或切分截断。",
                location=location,
                snippet=snippet,
            )
        )
    for message, snippet in suspicious_token_warnings(text):
        issues.append(
            AuditIssue(
                "warning",
                "疑似错误 token",
                chapter,
                code,
                title,
                f"{text_kind}：{message}",
                "人工确认是否为 OCR、清洗或转义残留；本 QA 不自动修复。",
                location=location,
                snippet=snippet,
            )
        )
    return issues


def expected_unit_type_from_marker(title: str) -> str | None:
    # Conservative check: only leading textbook markers are treated as expected
    # unit types. This avoids flagging ordinary phrases such as “定义域”.
    cleaned = title.strip()
    marker_rules = [
        (re.compile(r"^例题?\s*\d*\.?\d*"), "example"),
        (re.compile(r"^定义\s*\d*\.?\d*"), "definition"),
        (re.compile(r"^定理\s*\d*\.?\d*|^定理\d"), "theorem"),
        (re.compile(r"^习题\s*\d*\.?\d*"), "exercise"),
    ]
    for pattern, expected in marker_rules:
        if pattern.search(cleaned):
            return expected
    return None


def audit_unit_marker(
    *,
    chapter: str,
    code: str,
    unit_title: str,
    unit_type: str,
    location: str,
) -> list[AuditIssue]:
    expected = expected_unit_type_from_marker(unit_title)
    if not expected or expected == unit_type:
        return []
    return [
        AuditIssue(
            "warning",
            "marker 类型疑似误识别",
            chapter,
            code,
            unit_title,
            f"标题 marker 对应 `{expected}`，但当前内容单元类型为 `{unit_type}`。",
            "检查 marker 正则和标题清洗结果；必要时扩展 classify_unit 规则。",
            location=location,
            snippet=compact_text(unit_title, 180),
        )
    ]


def audit_unit_length(
    *,
    chapter: str,
    code: str,
    unit_title: str,
    content: str,
    location: str,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    nonspace_length = len(re.sub(r"\s+", "", content))
    if nonspace_length < UNIT_MIN_NONSPACE_CHARS:
        issues.append(
            AuditIssue(
                "warning",
                "内容单元过短",
                chapter,
                code,
                unit_title,
                f"正文去除空白后仅 {nonspace_length} 字符，低于阈值 {UNIT_MIN_NONSPACE_CHARS}。",
                "检查是否为空 marker、目录残留或切分噪声。",
                location=location,
                snippet=compact_text(content, 180),
            )
        )
    if len(content) > UNIT_MAX_CHARS:
        issues.append(
            AuditIssue(
                "warning",
                "内容单元过长",
                chapter,
                code,
                unit_title,
                f"正文长度 {len(content)}，超过阈值 {UNIT_MAX_CHARS}。",
                "检查是否需要在稳定定义/定理/例题/习题边界继续拆分。",
                location=location,
                snippet=compact_text(content, 180),
            )
        )
    return issues


def audit_point(chapter: SegmentedChapter, point: SegmentedKnowledgePoint) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    unit_type_counts = Counter(unit.unit_type for unit in point.units)
    point_base_code = base_code(point.code)
    point_location = f"{chapter.title} / 知识点"

    issues.extend(
        audit_title_text(
            chapter=chapter.title,
            code=point.code,
            title=point.title,
            location=point_location,
            title_kind="知识点",
            max_chars=POINT_TITLE_MAX_CHARS,
        )
    )
    issues.extend(
        audit_latex_text(
            chapter=chapter.title,
            code=point.code,
            title=point.title,
            location=point_location,
            text=point.title,
            text_kind="知识点标题",
        )
    )
    issues.extend(
        audit_latex_text(
            chapter=chapter.title,
            code=point.code,
            title=point.title,
            location=f"{chapter.title} / 知识点正文",
            text=point.raw_markdown,
            text_kind="知识点正文",
        )
    )

    for unit_index, unit in enumerate(point.units, start=1):
        unit_location = f"{chapter.title} / {point.code} / 单元 {unit_index} ({unit.unit_type})"
        issues.extend(
            audit_title_text(
                chapter=chapter.title,
                code=point.code,
                title=unit.title,
                location=unit_location,
                title_kind="内容单元",
                max_chars=UNIT_TITLE_MAX_CHARS,
            )
        )
        issues.extend(
            audit_latex_text(
                chapter=chapter.title,
                code=point.code,
                title=unit.title,
                location=unit_location,
                text=unit.title,
                text_kind="内容单元标题",
            )
        )
        issues.extend(
            audit_latex_text(
                chapter=chapter.title,
                code=point.code,
                title=unit.title,
                location=f"{unit_location} / 正文",
                text=unit.content,
                text_kind="内容单元正文",
            )
        )
        issues.extend(
            audit_unit_marker(
                chapter=chapter.title,
                code=point.code,
                unit_title=unit.title,
                unit_type=unit.unit_type,
                location=unit_location,
            )
        )
        issues.extend(
            audit_unit_length(
                chapter=chapter.title,
                code=point.code,
                unit_title=unit.title,
                content=unit.content,
                location=f"{unit_location} / 正文",
            )
        )

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
                location=f"{chapter.title} / 知识点正文",
                snippet=compact_text(point.raw_markdown, 180),
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
                location=f"{chapter.title} / 知识点正文",
                snippet=compact_text(point.raw_markdown, 180),
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
                location=f"{chapter.title} / 知识点",
                snippet=compact_text(point.raw_markdown, 180),
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
                location=f"{chapter.title} / 知识点",
                snippet=compact_text(point.raw_markdown, 180),
            )
        )

    return issues


def collect_issues(chapters: list[SegmentedChapter]) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for chapter in chapters:
        for point in chapter.points:
            issues.extend(audit_point(chapter, point))
    severity_order = {"high": 0, "warning": 1, "medium": 2, "review": 3}
    return sorted(issues, key=lambda item: (severity_order.get(item.severity, 9), item.chapter, item.code, item.category))


def append_title_issue_section(lines: list[str], issues: list[AuditIssue]) -> None:
    title_issues = [issue for issue in issues if issue.category in TITLE_ISSUE_CATEGORIES]
    lines.extend(["", "## 标题与公式异常", ""])
    if not title_issues:
        lines.append("未发现明显异常。")
        return
    lines.extend(["| 严重度 | 类型 | 位置 | code | title | 说明 |", "|---|---|---|---|---|---|"])
    for issue in title_issues:
        lines.append(
            f"| {markdown_cell(issue.severity)} | {markdown_cell(issue.category)} | "
            f"{markdown_cell(issue.display_location)} | `{markdown_cell(issue.code)}` | "
            f"{markdown_cell(issue.title)} | {markdown_cell(issue.details)} |"
        )


def append_latex_issue_section(lines: list[str], issues: list[AuditIssue]) -> None:
    latex_issues = [issue for issue in issues if issue.category in LATEX_ISSUE_CATEGORIES]
    lines.extend(["", "## LaTeX 可疑项", ""])
    if not latex_issues:
        lines.append("未发现明显异常。")
        return
    lines.extend(["| 严重度 | 位置 | code | 片段 | 说明 |", "|---|---|---|---|---|"])
    for issue in latex_issues:
        lines.append(
            f"| {markdown_cell(issue.severity)} | {markdown_cell(issue.display_location)} | "
            f"`{markdown_cell(issue.code)}` | {markdown_cell(issue.snippet)} | {markdown_cell(issue.details)} |"
        )


def append_marker_issue_section(lines: list[str], issues: list[AuditIssue]) -> None:
    marker_issues = [issue for issue in issues if issue.category in MARKER_ISSUE_CATEGORIES]
    lines.extend(["", "## Marker 识别异常", ""])
    if not marker_issues:
        lines.append("未发现明显异常。")
        return
    lines.extend(["| 严重度 | 位置 | code | title | 说明 |", "|---|---|---|---|---|"])
    for issue in marker_issues:
        lines.append(
            f"| {markdown_cell(issue.severity)} | {markdown_cell(issue.display_location)} | "
            f"`{markdown_cell(issue.code)}` | {markdown_cell(issue.title)} | {markdown_cell(issue.details)} |"
        )


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
        "- 本次 QA 只做检测，不自动修复教材内容。",
        "- 检测结果用于提升比赛展示可信度，帮助提前发现公式误入标题、LaTeX 残留和 marker 识别异常。",
        "- 当前规则是启发式规则，可能存在少量误报，需要人工复核后再决定是否调整清洗或切分规则。",
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

    append_title_issue_section(lines, issues)
    append_latex_issue_section(lines, issues)
    append_marker_issue_section(lines, issues)

    lines.extend(["", "## 待复核问题", ""])
    if issues:
        lines.extend(["| 级别 | 类型 | 位置 | 知识点 | 详情 | 建议 |", "|---|---|---|---|---|---|"])
        for issue in issues:
            lines.append(
                f"| {markdown_cell(issue.severity)} | {markdown_cell(issue.category)} | {markdown_cell(issue.display_location)} | "
                f"`{markdown_cell(issue.code)}` {markdown_cell(issue.title)} | "
                f"{markdown_cell(issue.details)} | {markdown_cell(issue.recommendation)} |"
            )
    else:
        lines.append("未发现明显异常。")

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
    parser.add_argument("--input", help="清洗版或 MinerU Markdown 路径；默认优先 merged_full_formatted.md，缺失时回退到仓库样例")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help=f"QA 报告输出路径，默认 {DEFAULT_REPORT}")
    args = parser.parse_args()

    input_path = resolve_audit_input(args.input)
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
