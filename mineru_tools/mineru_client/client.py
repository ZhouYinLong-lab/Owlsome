"""
MinerU Client — 核心 API 客户端

支持两种模式:
  - MinerUClient: 精准解析 API（需 Token，异步提交→轮询）
  - AgentClient: 轻量解析 API（免登录，IP 限频）

特性:
  - 自动限流 + 指数退避重试
  - 大 PDF 自动拆分 → 并发处理 → 结果合并
  - 进度回调
  - 同步 & 异步调用（asyncio 可选）
"""

import os
import time
import json
import logging
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import (
    TaskStatus, TaskResult, BatchResult, ChunkResult, MergeResult,
    TaskState, ExtractProgress,
)
from .exceptions import (
    MinerUError, AuthenticationError, RateLimitError,
    TaskFailedError, TaskTimeoutError, FileTooLargeError,
)
from .rate_limiter import RateLimiter
from .pdf_splitter import PDFSplitter, merge_markdown_results
from .utils import extract_zip, read_markdown, ensure_dir, format_size

logger = logging.getLogger(__name__)


# ──────────────────────────── 常量 ────────────────────────────

BASE_URL = "https://mineru.net"
DEFAULT_POLL_INTERVAL = 2       # 轮询间隔（秒）
DEFAULT_TIMEOUT = 600           # 单任务超时（秒）
DEFAULT_MAX_WORKERS = 5         # 大 PDF 拆分后最大并发数
DEFAULT_RPS = 3.0               # 默认每秒请求数（保守）

# API 端点
ENDPOINT_CREATE_TASK = "/api/v4/extract/task"
ENDPOINT_QUERY_TASK = "/api/v4/extract/task/{task_id}"
ENDPOINT_BATCH_URLS = "/api/v4/file-urls/batch"
ENDPOINT_BATCH_RESULTS = "/api/v4/extract-results/batch/{batch_id}"
ENDPOINT_AGENT_URL = "/api/v1/agent/parse/url"
ENDPOINT_AGENT_FILE = "/api/v1/agent/parse/file"
ENDPOINT_AGENT_QUERY = "/api/v1/agent/parse/{task_id}"


# ──────────────────────────── 客户端 ────────────────────────────


class BaseClient:
    """底层 HTTP 客户端，封装鉴权、限流、重试。"""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = BASE_URL,
        requests_per_second: float = DEFAULT_RPS,
        max_retries: int = 5,
        timeout: int = 30,
    ):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # 限流器
        self._limiter = RateLimiter(
            requests_per_second=requests_per_second,
            max_retries=max_retries,
        )

        # HTTP Session（连接复用）
        self._session = requests.Session()
        self._session.headers.update(self._default_headers())

        # 挂载重试适配器（处理连接级重试）
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def _default_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _url(self, endpoint: str, **kwargs) -> str:
        path = endpoint.format(**kwargs)
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        endpoint_kwargs: Optional[Dict] = None,
    ) -> requests.Response:
        """带自动限流 + 重试的 HTTP 请求。"""
        url = self._url(endpoint, **(endpoint_kwargs or {}))
        attempt = 0

        while True:
            self._limiter.wait_before_call()

            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    files=files,
                    timeout=self.timeout,
                )
            except requests.exceptions.Timeout:
                attempt += 1
                delay = self._limiter.retry.delay_for_attempt(attempt)
                logger.warning("Request timeout (attempt %d), retrying in %.1fs", attempt, delay)
                time.sleep(delay)
                continue
            except requests.exceptions.ConnectionError as e:
                attempt += 1
                delay = self._limiter.retry.delay_for_attempt(attempt)
                logger.warning("Connection error (attempt %d): %s, retrying in %.1fs", attempt, e, delay)
                time.sleep(delay)
                continue

            # 检查是否应重试
            if self._limiter.retry.should_retry(attempt, response.status_code):
                attempt += 1
                delay = self._limiter.handle_response(
                    attempt - 1, response.status_code, response.headers
                )
                logger.warning(
                    "HTTP %d (attempt %d), retrying in %.1fs",
                    response.status_code, attempt, delay,
                )
                time.sleep(delay)
                continue

            return response

    def _check_response(self, response: requests.Response) -> Dict[str, Any]:
        """校验 HTTP 响应并解析 JSON。"""
        if response.status_code == 401:
            raise AuthenticationError(
                "Invalid or missing API token. "
                "Get one at https://mineru.net/apiManage/docs"
            )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                f"Rate limited (HTTP 429). "
                f"Retry-After: {retry_after or 'unknown'}s",
                retry_after=retry_after,
            )

        try:
            data = response.json()
        except json.JSONDecodeError:
            response.raise_for_status()
            raise MinerUError(f"Invalid JSON response: {response.text[:500]}")

        # API 业务错误
        code = data.get("code", -1)
        if code != 0:
            msg = data.get("msg", "Unknown error")
            raise MinerUError(f"API error code={code}: {msg}")

        return data

    def close(self):
        """关闭 HTTP session。"""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ──────────────────────────── 精准解析客户端 ────────────────────────────


class MinerUClient(BaseClient):
    """MinerU 精准解析 API 客户端。

    需要 API Token（在 https://mineru.net/apiManage/docs 申请）。

    Args:
        token: API Token（必须）。
        base_url: API 基础 URL。
        requests_per_second: 每秒请求数限制（默认 3）。
        max_retries: 最大重试次数。
        timeout: HTTP 请求超时（秒）。
        poll_interval: 任务轮询间隔（秒）。
        task_timeout: 单任务最大等待时间（秒）。
        output_dir: 默认输出目录。
        auto_download: 是否自动下载并解压结果。

    Usage:
        client = MinerUClient(token="your-token")
        result = client.parse_url("https://example.com/doc.pdf")
        print(result.markdown_content)
    """

    def __init__(
        self,
        token: str,
        base_url: str = BASE_URL,
        requests_per_second: float = DEFAULT_RPS,
        max_retries: int = 5,
        timeout: int = 30,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        task_timeout: float = DEFAULT_TIMEOUT,
        output_dir: Optional[str] = None,
        auto_download: bool = True,
    ):
        if not token:
            raise AuthenticationError(
                "Token is required for precision API. "
                "Use AgentClient for token-free access."
            )
        super().__init__(
            token=token,
            base_url=base_url,
            requests_per_second=requests_per_second,
            max_retries=max_retries,
            timeout=timeout,
        )
        self.poll_interval = poll_interval
        self.task_timeout = task_timeout
        self.output_dir = output_dir or os.path.join(tempfile.gettempdir(), "mineru_output")
        self.auto_download = auto_download
        self._splitter = PDFSplitter()

    # ── 提交任务 ──

    def submit_task(
        self,
        file_url: str,
        model_version: str = "vlm",
        is_ocr: bool = False,
        enable_formula: bool = True,
        enable_table: bool = True,
        language: str = "ch",
        data_id: Optional[str] = None,
        callback: Optional[str] = None,
        seed: Optional[str] = None,
        extra_formats: Optional[List[str]] = None,
        page_ranges: Optional[str] = None,
        no_cache: bool = False,
        cache_tolerance: int = 900,
    ) -> str:
        """提交解析任务，返回 task_id。

        支持格式: PDF / DOC / DOCX / PPT / PPTX / XLS / XLSX / 图片 / HTML

        Args:
            file_url: 文件 URL。
            model_version: 模型版本 - "pipeline" / "vlm"(推荐) / "MinerU-HTML"。
            is_ocr: 是否启用 OCR。
            enable_formula: 是否识别公式。
            enable_table: 是否识别表格。
            language: 文档语言（默认 "ch"）。
            data_id: 业务数据自定义标识。
            callback: 回调通知 URL。
            seed: 回调签名随机串。
            extra_formats: 额外导出格式，如 ["docx", "html", "latex"]。
            page_ranges: 页码范围，如 "2,4-6"。
            no_cache: 是否绕过缓存。
            cache_tolerance: 缓存容忍时间（秒）。

        Returns:
            task_id 字符串。
        """
        payload = {
            "url": file_url,
            "model_version": model_version,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
            "enable_table": enable_table,
            "language": language,
            "no_cache": no_cache,
            "cache_tolerance": cache_tolerance,
        }
        if data_id:
            payload["data_id"] = data_id
        if callback:
            payload["callback"] = callback
        if seed:
            payload["seed"] = seed
        if extra_formats:
            payload["extra_formats"] = extra_formats
        if page_ranges:
            payload["page_ranges"] = page_ranges

        logger.info("Submitting task: %s (model=%s)", file_url[:80], model_version)
        response = self._request("POST", ENDPOINT_CREATE_TASK, json_data=payload)
        data = self._check_response(response)

        task_id = data["data"]["task_id"]
        logger.info("Task created: %s", task_id)
        return task_id

    # ── 查询状态 ──

    def get_task_status(self, task_id: str) -> TaskStatus:
        """查询任务状态。

        Args:
            task_id: 任务 ID。

        Returns:
            TaskStatus 对象。
        """
        endpoint = ENDPOINT_QUERY_TASK.format(task_id=task_id)
        response = self._request("GET", endpoint)
        data = self._check_response(response)

        task_data = data["data"]
        state = TaskState(task_data.get("state", "pending"))

        progress = None
        if "extract_progress" in task_data:
            ep = task_data["extract_progress"]
            progress = ExtractProgress(
                extracted_pages=ep.get("extracted_pages", 0),
                total_pages=ep.get("total_pages", 0),
                start_time=ep.get("start_time", ""),
            )

        return TaskStatus(
            task_id=task_data.get("task_id", task_id),
            state=state,
            data_id=task_data.get("data_id"),
            full_zip_url=task_data.get("full_zip_url"),
            err_msg=task_data.get("err_msg", ""),
            trace_id=data.get("trace_id"),
            progress=progress,
            raw_response=task_data,
        )

    # ── 等待完成 ──

    def wait_for_task(
        self,
        task_id: str,
        poll_interval: Optional[float] = None,
        timeout: Optional[float] = None,
        on_progress: Optional[Callable[[TaskStatus], None]] = None,
    ) -> TaskStatus:
        """轮询等待任务完成。

        Args:
            task_id: 任务 ID。
            poll_interval: 轮询间隔（默认使用实例配置）。
            timeout: 超时时间（默认使用实例配置）。
            on_progress: 进度回调，接收 TaskStatus。

        Returns:
            终态 TaskStatus。

        Raises:
            TaskTimeoutError: 超时未完成。
            TaskFailedError: 任务失败。
        """
        interval = poll_interval or self.poll_interval
        deadline = time.monotonic() + (timeout or self.task_timeout)

        while time.monotonic() < deadline:
            status = self.get_task_status(task_id)

            if on_progress:
                on_progress(status)

            if status.is_terminal:
                if status.is_failed:
                    raise TaskFailedError(task_id, status.err_msg)
                logger.info("Task %s completed", task_id)
                return status

            if status.progress:
                logger.debug(
                    "Task %s: %d/%d pages",
                    task_id,
                    status.progress.extracted_pages,
                    status.progress.total_pages,
                )

            time.sleep(interval)

        raise TaskTimeoutError(task_id, timeout or self.task_timeout)

    # ── 下载结果 ──

    def download_result(
        self,
        full_zip_url: str,
        output_dir: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> str:
        """下载并解压解析结果。

        Args:
            full_zip_url: ZIP 下载 URL（来自 TaskStatus.full_zip_url）。
            output_dir: 解压目录（默认使用实例配置）。
            file_name: 自定义文件名前缀。

        Returns:
            解压后的目录路径。
        """
        out = output_dir or self.output_dir
        ensure_dir(out)

        logger.info("Downloading result from %s", full_zip_url[:80])
        resp = requests.get(full_zip_url, timeout=120)
        resp.raise_for_status()

        # 写入临时 ZIP
        prefix = file_name or "result"
        zip_path = os.path.join(out, f"{prefix}.zip")
        with open(zip_path, "wb") as f:
            f.write(resp.content)

        # 解压
        extract_dir = os.path.join(out, prefix)
        extract_zip(zip_path, extract_dir)

        # 清理 ZIP（可选）
        try:
            os.remove(zip_path)
        except OSError:
            pass

        logger.info("Result extracted to %s", extract_dir)
        return extract_dir

    # ── 一站式：提交 + 等待 + 下载 ──

    def parse_url(
        self,
        file_url: str,
        output_dir: Optional[str] = None,
        file_name: Optional[str] = None,
        on_progress: Optional[Callable[[TaskStatus], None]] = None,
        **task_kwargs,
    ) -> TaskResult:
        """一站式解析：提交 URL → 轮询等待 → 下载结果。

        Args:
            file_url: 文件 URL。
            output_dir: 输出目录。
            file_name: 文件名前缀。
            on_progress: 进度回调。
            **task_kwargs: 传给 submit_task() 的其他参数。

        Returns:
            TaskResult 包含完整解析结果。
        """
        task_id = self.submit_task(file_url, **task_kwargs)
        status = self.wait_for_task(task_id, on_progress=on_progress)

        if not status.full_zip_url:
            raise MinerUError(f"Task {task_id} completed but no zip URL returned")

        out = output_dir or self.output_dir
        extract_dir = self.download_result(
            status.full_zip_url,
            output_dir=out,
            file_name=file_name or task_id[:8],
        )
        md_content = read_markdown(extract_dir)

        return TaskResult(
            task_id=task_id,
            file_name=file_name or file_url.rsplit("/", 1)[-1],
            full_zip_url=status.full_zip_url,
            local_zip_path=None,
            local_output_dir=extract_dir,
            markdown_content=md_content,
            metadata={"data_id": status.data_id, "trace_id": status.trace_id},
        )

    # ── 大 PDF 拆分解析 ──

    def parse_large_pdf(
        self,
        pdf_path: str,
        max_pages_per_chunk: int = 200,
        output_dir: Optional[str] = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
        on_chunk_progress: Optional[Callable[[int, int, TaskStatus], None]] = None,
        **task_kwargs,
    ) -> MergeResult:
        """处理超大 PDF：自动拆分 → 并发提交 → 合并结果。

        当 PDF 超过 200 页时自动拆分为多个子文件，并发处理，
        最后将每块的 Markdown 合并为一个完整文档。

        Args:
            pdf_path: 本地 PDF 路径。
            max_pages_per_chunk: 每块最大页数（默认 200）。
            output_dir: 输出目录。
            max_workers: 最大并发数。
            on_chunk_progress: 块进度回调 (chunk_index, total_chunks, TaskStatus)。
            **task_kwargs: 传给 submit_task() 的参数。

        Returns:
            MergeResult 含每块结果及合并后的 Markdown。
        """
        splitter = PDFSplitter(max_pages=max_pages_per_chunk)
        pages, size = splitter.get_pdf_info(pdf_path)

        logger.info(
            "Processing large PDF: %s (%d pages, %s)",
            pdf_path, pages, format_size(size),
        )

        # 拆分
        chunk_paths = splitter.split(pdf_path)
        total_chunks = len(chunk_paths)

        out = output_dir or os.path.join(self.output_dir, Path(pdf_path).stem)
        ensure_dir(out)

        chunk_results: List[ChunkResult] = []

        def _process_chunk(idx: int, chunk_path: str) -> ChunkResult:
            """处理单个块。"""
            page_start = idx * max_pages_per_chunk + 1
            page_end = min((idx + 1) * max_pages_per_chunk, pages)

            try:
                # 对本地文件，需要先上传到可公开访问的 URL
                # 这里使用 file_url 方式——如果是本地文件，
                # 需要用户自行上传到 CDN 或使用 batch upload API
                #
                # 策略：先用 batch API 获取上传 URL，上传文件，再自动提交
                result = self._parse_local_chunk(
                    chunk_path,
                    output_dir=out,
                    chunk_index=idx,
                    **task_kwargs,
                )
                chunk_result = ChunkResult(
                    chunk_index=idx,
                    page_start=page_start,
                    page_end=page_end,
                    task_result=result,
                )
                logger.info(
                    "Chunk %d/%d (%d pages) completed: %s",
                    idx + 1, total_chunks, page_end - page_start + 1,
                    result.task_id,
                )
            except Exception as e:
                logger.error("Chunk %d failed: %s", idx + 1, e)
                chunk_result = ChunkResult(
                    chunk_index=idx,
                    page_start=page_start,
                    page_end=page_end,
                    error=str(e),
                )

            return chunk_result

        # 并发处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_process_chunk, i, path): i
                for i, path in enumerate(chunk_paths)
            }
            for future in as_completed(futures):
                chunk_result = future.result()
                chunk_results.append(chunk_result)

                if on_chunk_progress:
                    status = (
                        chunk_result.task_result
                        and TaskStatus(
                            task_id=chunk_result.task_result.task_id,
                            state=TaskState.DONE,
                        )
                        or TaskStatus(
                            task_id="",
                            state=TaskState.FAILED,
                            err_msg=chunk_result.error or "",
                        )
                    )
                    on_chunk_progress(
                        chunk_result.chunk_index,
                        total_chunks,
                        status,
                    )

        # 按 chunk_index 排序
        chunk_results.sort(key=lambda c: c.chunk_index)

        # 合并 Markdown
        merged_md = merge_markdown_results(chunk_results)
        if merged_md:
            merged_path = os.path.join(out, "merged_full.md")
            with open(merged_path, "w", encoding="utf-8") as f:
                f.write(merged_md)
            logger.info("Merged markdown written to %s", merged_path)

        # 清理临时文件
        splitter.cleanup_chunks(chunk_paths)

        return MergeResult(
            original_file=pdf_path,
            total_pages=pages,
            chunks=chunk_results,
            merged_markdown=merged_md,
            merged_output_dir=out,
        )

    def _parse_local_chunk(
        self,
        chunk_path: str,
        output_dir: str,
        chunk_index: int,
        **task_kwargs,
    ) -> TaskResult:
        """通过批量上传 API 处理本地文件块。

        流程: 申请上传 URL → PUT 上传文件 → 系统自动创建任务 → 轮询等待 → 下载。
        """
        file_name = os.path.basename(chunk_path)

        # Step 1: 申请批量上传 URL
        payload = {
            "files": [{"name": file_name}],
            "model_version": task_kwargs.pop("model_version", "vlm"),
        }
        # 透传其他参数
        for key in ("is_ocr", "enable_formula", "enable_table", "language"):
            if key in task_kwargs:
                payload[key] = task_kwargs[key]

        logger.debug("Requesting upload URL for chunk %d: %s", chunk_index, file_name)
        response = self._request("POST", ENDPOINT_BATCH_URLS, json_data=payload)
        data = self._check_response(response)

        batch_id = data["data"]["batch_id"]
        file_urls = data["data"]["file_urls"]

        if not file_urls:
            raise MinerUError("No upload URL returned for chunk")

        upload_url = file_urls[0]

        # Step 2: PUT 上传文件
        # 不发送 Content-Type，避免与预签名 URL 的签名不匹配导致 403
        logger.debug("Uploading chunk %d to %s", chunk_index, upload_url[:80])
        with open(chunk_path, "rb") as f:
            upload_resp = requests.put(
                upload_url,
                data=f,
                timeout=300,
            )
        if upload_resp.status_code not in (200, 201, 204):
            logger.error(
                "Upload chunk %d failed: HTTP %d, body: %s",
                chunk_index, upload_resp.status_code, upload_resp.text[:500],
            )
            raise MinerUError(
                f"Failed to upload chunk {chunk_index}: "
                f"HTTP {upload_resp.status_code} — {upload_resp.text[:200]}"
            )

        # Step 3: 轮询 batch 结果（系统自动提交任务）
        # 文档: GET /api/v4/extract-results/batch/{batch_id}
        # 返回 extract_result 数组，每项含 state / full_zip_url / err_msg
        logger.debug("Polling batch %s for chunk %d", batch_id, chunk_index)

        deadline = time.monotonic() + (self.task_timeout or 600)
        extract_item = None

        while time.monotonic() < deadline:
            batch_resp = self._request(
                "GET", ENDPOINT_BATCH_RESULTS, endpoint_kwargs={"batch_id": batch_id}
            )
            batch_data = self._check_response(batch_resp)
            results = batch_data.get("data", {}).get("extract_result", [])

            if results:
                extract_item = results[0]
                state = extract_item.get("state", "")

                if state == "done":
                    logger.info("Batch chunk %d completed", chunk_index)
                    break
                elif state == "failed":
                    raise TaskFailedError(
                        batch_id,
                        extract_item.get("err_msg", "Batch parse failed"),
                    )
                elif state in ("running", "pending", "converting"):
                    logger.debug(
                        "Chunk %d: state=%s", chunk_index, state,
                    )

            time.sleep(self.poll_interval)

        if not extract_item or extract_item.get("state") != "done":
            raise TaskTimeoutError(
                f"batch {batch_id} chunk {chunk_index}",
                self.task_timeout,
            )

        full_zip_url = extract_item.get("full_zip_url", "")

        # Step 4: 下载结果
        if not full_zip_url:
            raise MinerUError(f"No zip URL for chunk {chunk_index} (batch {batch_id})")

        chunk_output = os.path.join(output_dir, f"chunk_{chunk_index:03d}")
        extract_dir = self.download_result(
            full_zip_url,
            output_dir=chunk_output,
            file_name=f"chunk_{chunk_index:03d}",
        )
        md_content = read_markdown(extract_dir)

        return TaskResult(
            task_id=batch_id,
            file_name=file_name,
            full_zip_url=full_zip_url,
            local_output_dir=extract_dir,
            markdown_content=md_content,
            metadata={"batch_id": batch_id, "chunk_index": chunk_index},
        )

    # ── 批量解析（URL 方式） ──

    def batch_parse_urls(
        self,
        file_urls: List[str],
        output_dir: Optional[str] = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
        on_progress: Optional[Callable[[int, int], None]] = None,
        **task_kwargs,
    ) -> BatchResult:
        """批量解析多个文件 URL（并发）。

        Args:
            file_urls: 文件 URL 列表。
            output_dir: 输出目录。
            max_workers: 最大并发数。
            on_progress: 进度回调 (completed, total)。
            **task_kwargs: 传给 parse_url() 的参数。

        Returns:
            BatchResult。
        """
        out = output_dir or self.output_dir
        results: List[TaskResult] = []
        total = len(file_urls)

        def _process_url(idx: int, url: str) -> TaskResult:
            try:
                name = url.rsplit("/", 1)[-1].split("?")[0] or f"file_{idx}"
                return self.parse_url(
                    url,
                    output_dir=os.path.join(out, name),
                    file_name=name,
                    **task_kwargs,
                )
            except Exception as e:
                logger.error("Batch item %d failed: %s", idx, e)
                return TaskResult(
                    task_id="",
                    file_name=url,
                    error=str(e),
                )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_process_url, i, url): i
                for i, url in enumerate(file_urls)
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if on_progress:
                    on_progress(len(results), total)

        success = sum(1 for r in results if r.error is None)
        failed = total - success

        return BatchResult(
            total=total,
            success_count=success,
            failed_count=failed,
            results=results,
        )


# ──────────────────────────── Agent 轻量客户端 ────────────────────────────


class AgentClient(BaseClient):
    """Agent 轻量解析 API 客户端（免 Token，IP 限频）。

    限制:
      - 文件 ≤ 10MB
      - 页数 ≤ 20
      - 仅输出 Markdown（CDN 链接）
      - 单文件、不支持批量

    Usage:
        client = AgentClient()
        result = client.parse_url("https://example.com/small.pdf")
        print(result.markdown_content)
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        requests_per_second: float = 1.0,  # Agent API 限频更严格
        max_retries: int = 3,
        timeout: int = 30,
        poll_interval: float = 3.0,
        task_timeout: float = 300,
    ):
        super().__init__(
            token=None,
            base_url=base_url,
            requests_per_second=requests_per_second,
            max_retries=max_retries,
            timeout=timeout,
        )
        self.poll_interval = poll_interval
        self.task_timeout = task_timeout

    def parse_url(
        self,
        file_url: str,
        on_progress: Optional[Callable] = None,
    ) -> TaskResult:
        """通过 URL 解析文件（Agent 模式）。

        Args:
            file_url: 文件 URL（文件 ≤ 10MB, ≤ 20 页）。
            on_progress: 进度回调。

        Returns:
            TaskResult。
        """
        payload = {"url": file_url}

        logger.info("Agent parse URL: %s", file_url[:80])
        response = self._request("POST", ENDPOINT_AGENT_URL, json_data=payload)
        data = self._check_response(response)

        task_id = data["data"]["task_id"]
        logger.info("Agent task created: %s", task_id)

        # 轮询
        status = self._wait_agent_task(task_id, on_progress=on_progress)

        # Agent API 返回的是 markdown CDN URL
        md_url = status.raw_response.get("markdown_url", "")
        md_content = None
        if md_url:
            try:
                md_resp = requests.get(md_url, timeout=30)
                md_content = md_resp.text
            except Exception as e:
                logger.warning("Failed to download markdown: %s", e)

        return TaskResult(
            task_id=task_id,
            file_name=file_url.rsplit("/", 1)[-1],
            markdown_content=md_content,
            metadata={"markdown_url": md_url},
        )

    def parse_file(
        self,
        file_path: str,
        language: str = "ch",
        enable_table: bool = True,
        is_ocr: bool = False,
        enable_formula: bool = True,
        page_range: Optional[str] = None,
        on_progress: Optional[Callable] = None,
    ) -> TaskResult:
        """通过本地文件上传解析（Agent 模式，签名上传）。

        流程: POST 获取上传 URL → PUT 上传 → 轮询 → 返回 Markdown。

        Args:
            file_path: 本地文件路径（≤10MB, ≤20 页）。
            language: 文档语言。
            enable_table: 是否开启表格识别。
            is_ocr: 是否开启 OCR。
            enable_formula: 是否开启公式识别。
            page_range: 页码范围（如 "1-10"）。
            on_progress: 进度回调。

        Returns:
            TaskResult。
        """
        file_name = os.path.basename(file_path)
        payload = {
            "file_name": file_name,
            "language": language,
            "enable_table": enable_table,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
        }
        if page_range:
            payload["page_range"] = page_range

        logger.info("Agent parse file: %s", file_name)
        response = self._request("POST", ENDPOINT_AGENT_FILE, json_data=payload)
        data = self._check_response(response)

        task_id = data["data"]["task_id"]
        file_url = data["data"]["file_url"]

        # PUT 上传文件（不设 Content-Type）
        logger.debug("Uploading %s to agent OSS", file_name)
        with open(file_path, "rb") as f:
            upload_resp = requests.put(file_url, data=f, timeout=120)
        if upload_resp.status_code not in (200, 201, 204):
            raise MinerUError(
                f"Agent file upload failed: "
                f"HTTP {upload_resp.status_code} — {upload_resp.text[:200]}"
            )
        logger.info("Agent file uploaded for task %s", task_id)

        # 轮询
        status = self._wait_agent_task(task_id, on_progress=on_progress)

        md_url = status.raw_response.get("markdown_url", "")
        md_content = None
        if md_url:
            try:
                md_resp = requests.get(md_url, timeout=30)
                md_content = md_resp.text
            except Exception as e:
                logger.warning("Failed to download markdown: %s", e)

        return TaskResult(
            task_id=task_id,
            file_name=file_name,
            markdown_content=md_content,
            metadata={"markdown_url": md_url},
        )

    def _wait_agent_task(
        self,
        task_id: str,
        on_progress: Optional[Callable] = None,
    ) -> TaskStatus:
        """等待 Agent 任务完成。"""
        endpoint = ENDPOINT_AGENT_QUERY.format(task_id=task_id)
        deadline = time.monotonic() + self.task_timeout

        while time.monotonic() < deadline:
            response = self._request("GET", endpoint)
            data = self._check_response(response)
            task_data = data["data"]

            state = TaskState(task_data.get("state", "pending"))
            status = TaskStatus(
                task_id=task_id,
                state=state,
                raw_response=task_data,
            )

            if on_progress:
                on_progress(status)

            if status.is_terminal:
                if status.is_failed:
                    raise TaskFailedError(
                        task_id, task_data.get("err_msg", "Agent parse failed")
                    )
                return status

            time.sleep(self.poll_interval)

        raise TaskTimeoutError(task_id, self.task_timeout)
