from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SegmentedUnit:
    unit_type: str
    title: str
    content: str


@dataclass
class SegmentedKnowledgePoint:
    code: str
    title: str
    summary: str
    raw_markdown: str
    difficulty: int
    tags: list[str] = field(default_factory=list)
    units: list[SegmentedUnit] = field(default_factory=list)


@dataclass
class SegmentedChapter:
    code: str
    title: str
    raw_markdown: str
    order_index: int
    points: list[SegmentedKnowledgePoint] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


SECTION_START_RE = re.compile(r"^#{1,3}\s+5\.(1|2)\s+(.+)$", re.MULTILINE)
SUBSECTION_RE = re.compile(r"^#{1,3}\s+(5\.(?:1|2)\.\d+)\s+(.+)$", re.MULTILINE)
CHAPTER_RE = re.compile(r"^#{1,3}\s+第\s*(\d+)\s*章\s+(.+?)\s*$", re.MULTILINE)
NUMBERED_SECTION_RE = re.compile(r"^#{1,4}\s+(\d+\.\d+)\s+(.+?)\s*$", re.MULTILINE)
NUMBERED_SUBSECTION_RE = re.compile(r"^#{1,5}\s+(\d+\.\d+\.\d+)\s+(.+?)\s*$", re.MULTILINE)

# 这些 marker 是第一版规则切分的核心：教材文本有比较稳定的“定义/定理/例/习题”
# 起始格式。先用规则保证离线可演示，再给 LLM 增强留下入口。
UNIT_MARKER_RE = re.compile(
    r"^\s*(?:>\s*)?(?:\[\![^\]]+\]\s*)?(?:#{1,6}\s*)?(?:\*\*)?(定义\s*(?:\d+\.\d+\.\d+)?.*|定理\s*(?:\d+\.\d+\.\d+)?.*|定理\d+\.\d+\.\d+.*|推论\s*(?:\d+\.\d+\.\d+)?.*|证明.*|注\s*(?:\d+\.\d+\.\d+)?.*|例\s*(?:\d+\.\d+\.\d+)?.*|例\d+\.\d+\.\d+.*|习题\s*\d+(?:\.\d+)?.*)$",
    re.MULTILINE,
)
GENERIC_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
LONG_POINT_THRESHOLD = 18000
TARGET_SPLIT_CHARS = 12000


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.replace("……", " ")).strip()


def extract_demo_scope(markdown: str) -> str:
    """Extract the real chapter body for 5.1-5.2, skipping the table of contents."""
    chapter_matches = list(re.finditer(r"^#{1,3}\s+第\s*5\s*章\s+多元函数微分学\s*$", markdown, re.MULTILINE))
    if not chapter_matches:
        raise ValueError("没有找到第 5 章正文，无法导入样例。")

    # Cleaned Markdown may contain a table of contents before the real chapter
    # body. Try every chapter heading and keep the first range that contains
    # substantial subsection content, instead of blindly accepting the TOC.
    for chapter_match in chapter_matches:
        start_match = SECTION_START_RE.search(markdown, chapter_match.end())
        if not start_match:
            continue

        next_section = re.search(r"^#{1,3}\s+5\.3\s+", markdown[start_match.start() :], re.MULTILINE)
        if not next_section:
            continue
        end = start_match.start() + next_section.start()
        scope = markdown[start_match.start() : end].strip()
        if len(scope) > 5000 and SUBSECTION_RE.search(scope):
            return scope

    raise ValueError("没有找到 5.1-5.2 正文范围，无法稳定截取样例。")


def split_subsections(scope_markdown: str) -> list[tuple[str, str, str]]:
    """Return (code, title, body) for 5.1.1 ... 5.2.4."""
    matches = list(SUBSECTION_RE.finditer(scope_markdown))
    if not matches:
        raise ValueError("样例范围内没有找到小节标题。")

    sections: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(scope_markdown)
        code = match.group(1)
        title = normalize_title(match.group(2))
        body = scope_markdown[start:end].strip()
        sections.append((code, title, body))
    return sections


def classify_unit(marker: str) -> str:
    marker = marker.lstrip("#").strip()
    if marker.startswith("定义"):
        return "definition"
    if marker.startswith("定理"):
        return "theorem"
    if marker.startswith("推论"):
        return "theorem"
    if marker.startswith("例"):
        return "example"
    if marker.startswith("习题"):
        return "exercise"
    return "explanation"


def split_units(body: str) -> list[SegmentedUnit]:
    """Split a subsection into typed units, preserving original Markdown snippets."""
    units: list[SegmentedUnit] = []
    matches = list(UNIT_MARKER_RE.finditer(body))
    intro = body[: matches[0].start()].strip() if matches else body.strip()
    if intro:
        units.append(SegmentedUnit("explanation", "教材讲解", intro))

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        marker = match.group(1).strip()
        units.append(
            SegmentedUnit(
                unit_type=classify_unit(marker),
                title=normalize_title(marker.lstrip("#").strip())[:120],
                content=content,
            )
        )
    return units


def summarize(code: str, title: str, units: list[SegmentedUnit]) -> str:
    """Offline summary used when no LLM key is configured."""
    unit_types = {unit.unit_type for unit in units}
    fragments: list[str] = []
    if "definition" in unit_types:
        fragments.append("核心定义")
    if "theorem" in unit_types:
        fragments.append("重要定理")
    if "example" in unit_types:
        fragments.append("例题训练")
    if not fragments:
        fragments.append("基础讲解")
    return f"{code} {title}：包含{'、'.join(fragments)}，适合作为公共知识库的一个学习单元。"


def make_tags(title: str, units: list[SegmentedUnit]) -> list[str]:
    tags = ["微积分", "多元函数"]
    if "极限" in title:
        tags.append("极限")
    if "连续" in title:
        tags.append("连续性")
    if "偏导" in title:
        tags.append("偏导数")
    if "微分" in title:
        tags.append("全微分")
    if any(unit.unit_type == "example" for unit in units):
        tags.append("例题")
    if "积分" in title:
        tags.append("积分")
    if "级数" in title:
        tags.append("级数")
    if "方程" in title:
        tags.append("微分方程")
    return tags


def split_full_textbook(markdown: str) -> list[SegmentedChapter]:
    """Split a cleaned full textbook into chapters and learning points.

    This is intentionally rule-only for the first full-book importer. It gives
    us deterministic local runs and a reportable warning surface before any LLM
    summary or semantic validation is introduced.
    """
    chapters: list[SegmentedChapter] = []
    chapter_matches = list(CHAPTER_RE.finditer(markdown))
    if not chapter_matches:
        return chapters

    seen_chapter_codes: set[str] = set()
    for match_index, match in enumerate(chapter_matches):
        code = match.group(1)
        title = normalize_title(match.group(2))
        start = match.end()
        end = chapter_matches[match_index + 1].start() if match_index + 1 < len(chapter_matches) else len(markdown)
        body = markdown[start:end].strip()

        # Cleaned textbooks can repeat chapter names in a table of contents.
        # Keep only chapter bodies that contain substantial numbered sections.
        if code in seen_chapter_codes or len(body) < 1000 or not NUMBERED_SECTION_RE.search(body):
            continue
        seen_chapter_codes.add(code)

        chapter = SegmentedChapter(
            code=code,
            title=f"第 {code} 章 {title}",
            raw_markdown=body,
            order_index=int(code),
        )
        chapter.points = split_chapter_points(code, body)
        if not chapter.points:
            chapter.warnings.append("未识别到知识点，已跳过导入。")
        chapters.append(chapter)
    return chapters


def split_chapter_points(chapter_code: str, chapter_body: str) -> list[SegmentedKnowledgePoint]:
    # Prefer subsection-level knowledge points such as 5.1.1. If a chapter only
    # has section headings, each section becomes one coarse knowledge point.
    subsection_matches = [
        match for match in NUMBERED_SUBSECTION_RE.finditer(chapter_body)
        if match.group(1).startswith(f"{chapter_code}.")
    ]
    if subsection_matches:
        return _points_from_matches(chapter_body, subsection_matches)

    section_matches = [
        match for match in NUMBERED_SECTION_RE.finditer(chapter_body)
        if match.group(1).startswith(f"{chapter_code}.")
    ]
    return _points_from_matches(chapter_body, section_matches)


def _points_from_matches(markdown: str, matches: list[re.Match[str]]) -> list[SegmentedKnowledgePoint]:
    points: list[SegmentedKnowledgePoint] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        code = match.group(1)
        title = normalize_title(match.group(2))
        body = markdown[start:end].strip()
        if len(body) < 40:
            continue
        units = split_units(body)
        point = SegmentedKnowledgePoint(
            code=code,
            title=title[:120],
            summary=summarize(code, title, units),
            raw_markdown=body,
            difficulty=2,
            tags=make_tags(title, units),
            units=units,
        )
        points.extend(split_oversized_point(point))
    return points


def split_oversized_point(point: SegmentedKnowledgePoint) -> list[SegmentedKnowledgePoint]:
    """Conservatively split very long points only at already detected unit boundaries.

    The full-book importer should make the demo easier to browse, but it must not
    invent semantic boundaries. If a long section has no stable definition /
    theorem / example / exercise markers, keep it intact and let the QA report
    flag it for manual review.
    """
    if len(point.raw_markdown) <= LONG_POINT_THRESHOLD or len(point.units) < 6:
        return [point]

    chunks: list[list[SegmentedUnit]] = []
    current: list[SegmentedUnit] = []
    current_len = 0
    for unit in point.units:
        unit_len = len(unit.content)
        if current and current_len + unit_len > TARGET_SPLIT_CHARS:
            chunks.append(current)
            current = []
            current_len = 0
        current.append(unit)
        current_len += unit_len
    if current:
        chunks.append(current)

    if len(chunks) < 2:
        return [point]

    split_points: list[SegmentedKnowledgePoint] = []
    for index, chunk_units in enumerate(chunks, start=1):
        code = f"{point.code}-{index}"
        title = f"{point.title}（{index}）"
        raw_markdown = "\n\n".join(unit.content for unit in chunk_units)
        split_points.append(
            SegmentedKnowledgePoint(
                code=code,
                title=title[:120],
                summary=summarize(code, title, chunk_units),
                raw_markdown=raw_markdown,
                difficulty=point.difficulty,
                tags=[*point.tags, "二次切分"],
                units=chunk_units,
            )
        )
    return split_points


def segment_markdown(markdown: str) -> list[SegmentedKnowledgePoint]:
    scope = extract_demo_scope(markdown)
    points: list[SegmentedKnowledgePoint] = []
    for order, (code, title, body) in enumerate(split_subsections(scope), start=1):
        units = split_units(body)
        points.append(
            SegmentedKnowledgePoint(
                code=code,
                title=title,
                summary=summarize(code, title, units),
                raw_markdown=body,
                difficulty=1 if code.startswith("5.1") else 2,
                tags=make_tags(title, units),
                units=units,
            )
        )
    return points


def segment_markdown_flexible(markdown: str) -> list[SegmentedKnowledgePoint]:
    """Segment user-uploaded Markdown without requiring the exact textbook layout.

    Personal spaces must be forgiving: if the precise 微积分 II 5.1-5.2 layout is
    present, reuse the proven textbook splitter; otherwise fall back to Markdown
    headings, and finally to a single overview point so uploads never dead-end.
    """
    try:
        return segment_markdown(markdown)
    except ValueError:
        pass

    points = segment_by_headings(markdown)
    if points:
        return points
    return [make_overview_point(markdown)]


def segment_by_headings(markdown: str) -> list[SegmentedKnowledgePoint]:
    matches = list(GENERIC_HEADING_RE.finditer(markdown))
    if not matches:
        return []

    points: list[SegmentedKnowledgePoint] = []
    for index, match in enumerate(matches[:10]):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        title = normalize_title(match.group(2))
        body = markdown[start:end].strip()
        if len(body) < 20:
            continue
        code = f"P{len(points) + 1}"
        units = split_units(body)
        points.append(
            SegmentedKnowledgePoint(
                code=code,
                title=title[:80],
                summary=summarize(code, title, units),
                raw_markdown=body,
                difficulty=1,
                tags=make_tags(title, units),
                units=units,
            )
        )
    return points


def make_overview_point(markdown: str) -> SegmentedKnowledgePoint:
    clipped = markdown.strip() or "上传内容为空。"
    unit = SegmentedUnit("explanation", "资料全文", clipped)
    return SegmentedKnowledgePoint(
        code="P1",
        title="资料概览",
        summary="未识别到稳定标题结构，系统已把全文作为一个可学习单元，便于继续问答和标记进度。",
        raw_markdown=clipped,
        difficulty=1,
        tags=["个人资料"],
        units=[unit],
    )
