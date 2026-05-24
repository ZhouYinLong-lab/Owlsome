"""
MinerU Client — PDF 拆分与合并工具

核心能力:
  - 将超大 PDF 拆分为 ≤ max_pages 页的多个子 PDF
  - 并发提交拆分后的子任务
  - 合并多个 Markdown 解析结果

依赖: pip install pypdf
"""

import os
import io
import tempfile
import logging
from typing import List, Optional, Callable, Tuple
from pathlib import Path

from .models import ChunkResult, MergeResult
from .exceptions import FileTooLargeError, TooManyPagesError

logger = logging.getLogger(__name__)

# API 限制常量
PRECISION_MAX_PAGES = 200       # 精准解析 API 单文件最大页数
PRECISION_MAX_SIZE_MB = 200     # 精准解析 API 单文件最大体积 (MB)
AGENT_MAX_PAGES = 20            # Agent API 单文件最大页数
AGENT_MAX_SIZE_MB = 10          # Agent API 单文件最大体积 (MB)


class PDFSplitter:
    """PDF 拆分器：将大 PDF 按页数拆分为子文件。

    Args:
        max_pages: 每个子文件的最大页数（默认 200，对应精准解析 API）。
        max_size_mb: 每个子文件的最大体积 MB（默认 200）。
        temp_dir: 临时文件目录，默认使用系统临时目录。
    """

    def __init__(
        self,
        max_pages: int = PRECISION_MAX_PAGES,
        max_size_mb: int = PRECISION_MAX_SIZE_MB,
        temp_dir: Optional[str] = None,
    ):
        self.max_pages = max_pages
        self.max_size_mb = max_size_mb
        self.temp_dir = temp_dir

    def get_pdf_info(self, pdf_path: str) -> Tuple[int, int]:
        """获取 PDF 的页数和文件大小。

        Returns:
            (page_count, file_size_bytes)
        """
        from pypdf import PdfReader

        file_size = os.path.getsize(pdf_path)
        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)
        return page_count, file_size

    def needs_split(self, pdf_path: str) -> bool:
        """判断 PDF 是否需要拆分。"""
        pages, size = self.get_pdf_info(pdf_path)
        return pages > self.max_pages or size > self.max_size_mb * 1024 * 1024

    def validate(self, pdf_path: str):
        """校验 PDF 是否可处理。若文件过大且无法拆分则抛出异常。"""
        pages, size = self.get_pdf_info(pdf_path)

        if size > self.max_size_mb * 1024 * 1024:
            raise FileTooLargeError(
                file_size=size,
                max_size=self.max_size_mb * 1024 * 1024,
            )

        if pages > self.max_pages:
            # 抛出提示——大 PDF 应走 parse_large_pdf()
            raise TooManyPagesError(pages=pages, max_pages=self.max_pages)

    def split(self, pdf_path: str) -> List[str]:
        """将 PDF 按 max_pages 拆分为多个临时子文件。

        Args:
            pdf_path: 原始 PDF 路径。

        Returns:
            子文件路径列表（在 temp_dir 下，调用者负责清理）。
        """
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        if total_pages <= self.max_pages:
            return [pdf_path]

        chunk_paths = []
        temp_dir = self.temp_dir or tempfile.mkdtemp(prefix="mineru_split_")

        for start in range(0, total_pages, self.max_pages):
            end = min(start + self.max_pages, total_pages)
            writer = PdfWriter()

            for i in range(start, end):
                writer.add_page(reader.pages[i])

            chunk_name = (
                f"{Path(pdf_path).stem}_"
                f"p{start + 1}-{end}.pdf"
            )
            chunk_path = os.path.join(temp_dir, chunk_name)
            with open(chunk_path, "wb") as f:
                writer.write(f)
            chunk_paths.append(chunk_path)

            logger.info(
                "Split chunk %d: pages %d-%d -> %s",
                len(chunk_paths), start + 1, end, chunk_path,
            )

        logger.info(
            "Split '%s' (%d pages) into %d chunks",
            pdf_path, total_pages, len(chunk_paths),
        )
        return chunk_paths

    def cleanup_chunks(self, chunk_paths: List[str]):
        """清理拆分生成的临时文件。"""
        for path in chunk_paths:
            try:
                if os.path.exists(path) and path != getattr(self, '_original', None):
                    os.remove(path)
            except OSError as e:
                logger.warning("Failed to clean up %s: %s", path, e)


def merge_markdown_results(
    chunks: List[ChunkResult],
    separator: str = "\n\n---\n\n",
) -> str:
    """合并多个块的 Markdown 解析结果为单一文档。

    Args:
        chunks: 有序的 ChunkResult 列表。
        separator: 块之间的分隔符。

    Returns:
        合并后的完整 Markdown 字符串。
    """
    parts = []
    for chunk in chunks:
        if chunk.task_result and chunk.task_result.markdown_content:
            header = f"<!-- Chunk {chunk.chunk_index + 1}: "
            header += f"Pages {chunk.page_start}-{chunk.page_end} -->\n\n"
            parts.append(header + chunk.task_result.markdown_content)
        elif chunk.error:
            parts.append(
                f"<!-- Chunk {chunk.chunk_index + 1}: "
                f"ERROR - {chunk.error} -->\n\n"
            )
    return separator.join(parts)
