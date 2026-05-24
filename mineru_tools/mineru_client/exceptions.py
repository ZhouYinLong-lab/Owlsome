"""
MinerU Client — 异常体系
"""


class MinerUError(Exception):
    """MinerU 全部异常的基类。"""
    pass


class AuthenticationError(MinerUError):
    """Token 无效或未提供（精准解析 API 需要）。"""
    pass


class RateLimitError(MinerUError):
    """触发 API 限流（HTTP 429 / IP 限频 / 每日配额用尽）。"""
    def __init__(self, message="", retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after  # 建议重试等待秒数


class TaskFailedError(MinerUError):
    """解析任务失败（state=failed）。"""
    def __init__(self, task_id, err_msg=""):
        super().__init__(f"Task {task_id} failed: {err_msg}")
        self.task_id = task_id
        self.err_msg = err_msg


class TaskTimeoutError(MinerUError):
    """轮询超时，任务在规定时间内未完成。"""
    def __init__(self, task_id, timeout):
        super().__init__(f"Task {task_id} timed out after {timeout}s")
        self.task_id = task_id
        self.timeout = timeout


class FileTooLargeError(MinerUError):
    """文件超过大小限制。"""
    def __init__(self, file_size, max_size, api_type="precision"):
        super().__init__(
            f"File size {file_size / 1024 / 1024:.1f}MB exceeds "
            f"{api_type} API limit of {max_size / 1024 / 1024:.1f}MB"
        )
        self.file_size = file_size
        self.max_size = max_size


class TooManyPagesError(MinerUError):
    """PDF 页数超过限制（拆分后仍建议处理）。"""
    def __init__(self, pages, max_pages):
        super().__init__(
            f"PDF has {pages} pages, exceeds limit of {max_pages}. "
            f"Use parse_large_pdf() for automatic splitting."
        )
        self.pages = pages
        self.max_pages = max_pages
