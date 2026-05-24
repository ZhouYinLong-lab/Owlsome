"""
MinerU Client — 数据模型 (dataclass)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class TaskState(str, Enum):
    """任务状态枚举。"""
    PENDING = "pending"       # 排队中
    RUNNING = "running"       # 正在解析
    CONVERTING = "converting" # 格式转换中
    DONE = "done"             # 完成
    FAILED = "failed"         # 失败

    @classmethod
    def terminal_states(cls):
        """终态：不需要再轮询的状态。"""
        return {cls.DONE, cls.FAILED}


@dataclass
class ExtractProgress:
    """解析进度信息。"""
    extracted_pages: int = 0
    total_pages: int = 0
    start_time: str = ""


@dataclass
class TaskStatus:
    """单任务状态快照。"""
    task_id: str
    state: TaskState
    data_id: Optional[str] = None
    full_zip_url: Optional[str] = None
    err_msg: str = ""
    trace_id: Optional[str] = None
    progress: Optional[ExtractProgress] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.state in TaskState.terminal_states()

    @property
    def is_success(self) -> bool:
        return self.state == TaskState.DONE

    @property
    def is_failed(self) -> bool:
        return self.state == TaskState.FAILED


@dataclass
class TaskResult:
    """单个文件的最终解析结果。"""
    task_id: str
    file_name: str
    full_zip_url: Optional[str] = None
    local_zip_path: Optional[str] = None
    local_output_dir: Optional[str] = None
    markdown_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class BatchResult:
    """批量解析汇总结果。"""
    batch_id: Optional[str] = None
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    results: List[TaskResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.success_count / self.total


@dataclass
class ChunkResult:
    """大 PDF 单块解析结果。"""
    chunk_index: int
    page_start: int
    page_end: int
    task_result: Optional[TaskResult] = None
    error: Optional[str] = None


@dataclass
class MergeResult:
    """大 PDF 拆分后合并结果。"""
    original_file: str
    total_pages: int
    chunks: List[ChunkResult] = field(default_factory=list)
    merged_markdown: Optional[str] = None
    merged_output_dir: Optional[str] = None

    @property
    def success_chunks(self) -> int:
        return sum(1 for c in self.chunks if c.task_result is not None)

    @property
    def failed_chunks(self) -> int:
        return sum(1 for c in self.chunks if c.error is not None)
