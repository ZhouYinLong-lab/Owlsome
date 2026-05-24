"""
MinerU Client — 工具函数
"""

import os
import io
import zipfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_zip(zip_path: str, output_dir: str) -> str:
    """解压 ZIP 文件到指定目录。

    Args:
        zip_path: ZIP 文件路径。
        output_dir: 解压目标目录。

    Returns:
        output_dir 路径。
    """
    os.makedirs(output_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(output_dir)
    logger.info("Extracted %s -> %s", zip_path, output_dir)
    return output_dir


def find_markdown_in_dir(directory: str) -> Optional[str]:
    """在目录中查找 Markdown 文件（优先 full.md）。

    Returns:
        Markdown 文件路径，若未找到返回 None。
    """
    # 优先查找 full.md
    full_md = os.path.join(directory, "full.md")
    if os.path.isfile(full_md):
        return full_md

    # 查找任意 .md 文件
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".md"):
                return os.path.join(root, f)
    return None


def read_markdown(directory_or_file: str) -> Optional[str]:
    """从目录或文件中读取 Markdown 内容。

    Args:
        directory_or_file: 目录路径或 .md 文件路径。

    Returns:
        Markdown 文本内容，或 None。
    """
    path = directory_or_file
    if os.path.isdir(path):
        md_file = find_markdown_in_dir(path)
        if not md_file:
            logger.warning("No markdown file found in %s", path)
            return None
        path = md_file

    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def ensure_dir(path: str) -> str:
    """确保目录存在并返回路径。"""
    os.makedirs(path, exist_ok=True)
    return path


def format_size(bytes_val: int) -> str:
    """人类可读的文件大小格式。"""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"
