from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
DETAILS_RE = re.compile(
    r"<details>\s*<summary>(?P<title>.*?)</summary>\s*(?P<body>.*?)</details>",
    re.DOTALL | re.IGNORECASE,
)
IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)")
HIGHLIGHT_RE = re.compile(r"==(.+?)==")


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_list(values: Iterable[str]) -> str:
    cleaned = [item.strip() for item in values if item and item.strip()]
    return "[" + ", ".join(yaml_quote(item) for item in cleaned) + "]"


def has_frontmatter(markdown: str) -> bool:
    return bool(FRONTMATTER_RE.match(markdown.lstrip("\ufeff")))


def build_frontmatter(
    *,
    title: str,
    source: str = "",
    tags: Iterable[str] = (),
    aliases: Iterable[str] = (),
    doc_type: str = "learning_material",
) -> str:
    """Create YAML frontmatter that Obsidian can read without plugins."""
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines = [
        "---",
        f"type: {yaml_quote(doc_type)}",
        f"title: {yaml_quote(title or 'Untitled')}",
        f"source: {yaml_quote(source)}",
        f"tags: {yaml_list(tags)}",
        f"aliases: {yaml_list(aliases)}",
        "obsidian_compatible: true",
        f"created_at: {yaml_quote(created)}",
        "---",
        "",
    ]
    return "\n".join(lines)


def details_to_callout(match: re.Match[str]) -> str:
    title = re.sub(r"\s+", " ", match.group("title")).strip() or "折叠内容"
    body = match.group("body").strip()
    # Obsidian callouts are blockquotes. The trailing '-' keeps long OCR/image
    # helper text collapsed by default inside Obsidian.
    quoted = "\n".join(f"> {line}" if line else ">" for line in body.splitlines())
    return f"> [!info]- {title}\n{quoted}"


def normalize_image_links(markdown: str) -> str:
    """Keep Markdown image links portable for both web rendering and Obsidian.

    MinerU commonly emits relative paths such as images/a.jpg. Obsidian accepts
    standard Markdown image syntax, so we preserve it and only normalize Windows
    separators that may appear after manual edits.
    """

    def repl(match: re.Match[str]) -> str:
        alt = match.group("alt")
        path = match.group("path").replace("\\", "/")
        return f"![{alt}]({path})"

    return IMAGE_RE.sub(repl, markdown)


def normalize_obsidian_markdown(
    markdown: str,
    *,
    title: str = "Untitled",
    source: str = "",
    tags: Iterable[str] = ("owlsome",),
    aliases: Iterable[str] = (),
    doc_type: str = "learning_material",
    add_frontmatter: bool = True,
) -> str:
    """Normalize Markdown into an Obsidian-compatible subset.

    The function intentionally avoids lossy rewrites. It adds frontmatter when
    missing, converts HTML details blocks to Obsidian callouts, and keeps math,
    wikilinks, task lists, and standard Markdown intact.
    """
    text = markdown.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff").strip()
    text = DETAILS_RE.sub(details_to_callout, text)
    text = normalize_image_links(text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    if add_frontmatter and not has_frontmatter(text):
        text = build_frontmatter(
            title=title,
            source=source,
            tags=tags,
            aliases=aliases,
            doc_type=doc_type,
        ) + text
    return text.rstrip() + "\n"


def title_from_path(path: str | Path) -> str:
    return Path(path).stem.replace("_", " ").strip() or "Untitled"

