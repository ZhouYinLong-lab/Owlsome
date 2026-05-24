"""
MinerU API Client — Python 封装库
===================================
高效、可靠的 MinerU 文档解析 API 封装，内置限流、重试、大 PDF 自动拆分合并。

支持两种 API 模式：
  - 🎯 精准解析 API  (需 Token，≤200MB/≤200页，支持批量)
  - ⚡ Agent 轻量解析 API (无需 Token，IP 限频，≤10MB/≤20页)

Usage:
    from mineru_client import MinerUClient

    client = MinerUClient(token="your-api-token")
    result = client.parse_pdf("document.pdf")
    print(result.markdown)
"""

from .client import MinerUClient, AgentClient
from .models import TaskStatus, TaskResult, BatchResult, ChunkResult, MergeResult
from .exceptions import (
    MinerUError,
    AuthenticationError,
    RateLimitError,
    TaskFailedError,
    TaskTimeoutError,
    FileTooLargeError,
    TooManyPagesError,
)
from .pdf_splitter import PDFSplitter, merge_markdown_results

__version__ = "1.0.0"
__all__ = [
    "MinerUClient",
    "AgentClient",
    "TaskStatus",
    "TaskResult",
    "BatchResult",
    "ChunkResult",
    "MergeResult",
    "MinerUError",
    "AuthenticationError",
    "RateLimitError",
    "TaskFailedError",
    "TaskTimeoutError",
    "FileTooLargeError",
    "TooManyPagesError",
    "PDFSplitter",
    "merge_markdown_results",
]
