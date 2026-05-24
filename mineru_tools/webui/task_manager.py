"""
Background task manager with SSE event streaming.
"""

import asyncio
import json
import logging
import queue
import threading
import time
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, AsyncGenerator

from . import db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from owlsome_core.obsidian import normalize_obsidian_markdown

logger = logging.getLogger(__name__)

# Captured main event loop for cross-thread DB updates
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def _capture_main_loop():
    global _main_loop
    if _main_loop is None:
        try:
            _main_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass


# ── SSE Event ──

@dataclass
class SSEEvent:
    db_id: int
    event: str  # "status", "progress", "batch", "chunk", "result", "error"
    data: Dict[str, Any] = field(default_factory=dict)


# ── In-memory event bus per task ──

_listeners: Dict[int, List[asyncio.Queue]] = {}
_lock = threading.Lock()


def _ensure_listener(db_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    with _lock:
        if db_id not in _listeners:
            _listeners[db_id] = []
        _listeners[db_id].append(q)
    return q


def _remove_listener(db_id: int, q: asyncio.Queue):
    with _lock:
        if db_id in _listeners:
            try:
                _listeners[db_id].remove(q)
            except ValueError:
                pass
            if not _listeners[db_id]:
                del _listeners[db_id]


def emit_event(event: SSEEvent):
    """Thread-safe: push an event to all listeners for a task."""
    logger.debug("emit %s db_id=%d data=%s", event.event, event.db_id, event.data)
    with _lock:
        queues = list(_listeners.get(event.db_id, []))
    for q in queues:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass

    # Map event to DB updates
    db_updates: Dict[str, Any] = {}
    if event.event == "status":
        db_updates["state"] = event.data.get("state", "")
    elif event.event == "progress":
        db_updates["progress_pages"] = event.data.get("extracted_pages", 0)
        db_updates["total_pages"] = event.data.get("total_pages", 0)
    elif event.event == "result":
        db_updates["state"] = "done"
        db_updates["full_zip_url"] = event.data.get("full_zip_url", "")
        db_updates["local_output_dir"] = event.data.get("local_output_dir", "")
        db_updates["markdown_content"] = event.data.get("markdown_content", "")
    elif event.event == "error":
        db_updates["state"] = "failed"
        db_updates["error_msg"] = event.data.get("error", "")
    elif event.event == "batch":
        db_updates["batch_completed"] = event.data.get("completed", 0)
        db_updates["batch_total"] = event.data.get("total", 0)
    elif event.event == "chunk":
        db_updates["chunk_index"] = event.data.get("chunk_index", 0)
        db_updates["chunk_total"] = event.data.get("chunk_total", 0)

    if db_updates and _main_loop is not None and not _main_loop.is_closed():
        asyncio.run_coroutine_threadsafe(
            _safe_db_update(event.db_id, db_updates), _main_loop
        )


async def _safe_db_update(db_id: int, updates: Dict[str, Any]):
    try:
        await db.update_task(db_id, updates)
    except Exception as e:
        logger.error("DB update failed for task %d: %s", db_id, e)


async def sse_stream(db_id: int) -> AsyncGenerator[str, None]:
    """SSE event stream generator for a task."""
    q = _ensure_listener(db_id)
    try:
        # Send initial state
        task = await db.get_task(db_id)
        if task:
            yield _format_sse("status", {
                "state": task["state"],
                "progress_pages": task["progress_pages"],
                "total_pages": task["total_pages"],
                "error_msg": task["error_msg"],
            })

        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
                yield _format_sse(event.event, event.data)
                if event.event in ("result", "error"):
                    break
            except asyncio.TimeoutError:
                yield _format_sse("heartbeat", {})
    finally:
        _remove_listener(db_id, q)


def _format_sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── Task runner (runs in background thread) ──

def run_mineru_task(
    db_id: int,
    task_type: str,
    token: str,
    file_url: str,
    model_version: str,
    language: str,
    is_ocr: bool,
    enable_formula: bool,
    enable_table: bool,
    local_file_path: Optional[str] = None,
    extra_formats: Optional[List[str]] = None,
    page_ranges: Optional[str] = None,
    no_cache: bool = False,
):
    """Run a MinerU task in a background thread and emit events."""
    from mineru_client import MinerUClient, AgentClient
    from mineru_client.models import TaskStatus as MinerUTaskStatus
    from mineru_client.exceptions import MinerUError

    def _emit(event: str, data: Dict[str, Any]):
        emit_event(SSEEvent(db_id=db_id, event=event, data=data))

    def _as_obsidian(markdown: str, file_name: str, source: str) -> str:
        # MinerU remains responsible for PDF parsing; this post-processing step
        # makes the resulting Markdown portable to Obsidian and Owlsome.
        return normalize_obsidian_markdown(
            markdown,
            title=Path(file_name or "MinerU Output").stem,
            source=source,
            tags=["owlsome", "mineru", "pdf"],
            doc_type="parsed_pdf",
        )

    try:
        emit_event(SSEEvent(db_id=db_id, event="status", data={"state": "running"}))

        if task_type in ("agent", "agent_file"):
            client = AgentClient(poll_interval=3.0, task_timeout=300)
            _emit("status", {"state": "running"})

            if task_type == "agent_file" and local_file_path:
                result = client.parse_file(
                    file_path=local_file_path,
                    language=language,
                    is_ocr=is_ocr,
                    enable_formula=enable_formula,
                    enable_table=enable_table,
                    page_range=page_ranges or None,
                    on_progress=lambda st: _emit("progress", {
                        "state": st.state.value,
                        "extracted_pages": 0,
                        "total_pages": 0,
                    }),
                )
            else:
                result = client.parse_url(file_url)
            _emit("result", {
                "task_id": result.task_id,
                "file_name": result.file_name,
                "markdown_content": _as_obsidian(
                    result.markdown_content or "",
                    result.file_name,
                    local_file_path or file_url,
                ),
                "metadata": result.metadata,
            })
            client.close()
        else:
            client = MinerUClient(
                token=token,
                poll_interval=2.0,
                task_timeout=600,
                output_dir=str(Path(__file__).resolve().parent.parent / "output"),
                auto_download=True,
            )

            if local_file_path and task_type == "precision_file":
                # Large PDF → split + merge
                _emit("status", {"state": "splitting"})
                merge_result = client.parse_large_pdf(
                    pdf_path=local_file_path,
                    max_pages_per_chunk=200,
                    max_workers=3,
                    model_version=model_version,
                    is_ocr=is_ocr,
                    enable_formula=enable_formula,
                    enable_table=enable_table,
                    language=language,
                    on_chunk_progress=lambda ci, ct, st: _emit("chunk", {
                        "chunk_index": ci + 1,
                        "chunk_total": ct,
                        "state": st.state.value,
                        "task_id": st.task_id,
                    }),
                )
                _emit("result", {
                    "task_id": "merged",
                    "file_name": Path(local_file_path).name,
                    "local_output_dir": merge_result.merged_output_dir or "",
                    "markdown_content": _as_obsidian(
                        merge_result.merged_markdown or "",
                        Path(local_file_path).name,
                        local_file_path or "",
                    ),
                    "chunks_done": merge_result.success_chunks,
                    "chunks_failed": merge_result.failed_chunks,
                    "total_pages": merge_result.total_pages,
                })
            else:
                # Standard URL parse
                result = client.parse_url(
                    file_url=file_url,
                    file_name=file_url.rsplit("/", 1)[-1].split("?")[0] if file_url else "output",
                    model_version=model_version,
                    language=language,
                    is_ocr=is_ocr,
                    enable_formula=enable_formula,
                    enable_table=enable_table,
                    extra_formats=extra_formats,
                    page_ranges=page_ranges,
                    no_cache=no_cache,
                    on_progress=lambda st: _emit("progress", {
                        "state": st.state.value,
                        "extracted_pages": st.progress.extracted_pages if st.progress else 0,
                        "total_pages": st.progress.total_pages if st.progress else 0,
                    }),
                )
                _emit("result", {
                    "task_id": result.task_id,
                    "file_name": result.file_name,
                    "full_zip_url": result.full_zip_url or "",
                    "local_output_dir": result.local_output_dir or "",
                    "markdown_content": _as_obsidian(
                        result.markdown_content or "",
                        result.file_name,
                        file_url,
                    ),
                    "metadata": result.metadata,
                })

            client.close()

    except MinerUError as e:
        logger.exception("MinerU task %d error", db_id)
        _emit("error", {"error": str(e), "code": type(e).__name__})
    except Exception as e:
        logger.exception("Unexpected task %d error", db_id)
        _emit("error", {"error": str(e), "code": "UnexpectedError"})


async def start_task_in_background(
    db_id: int,
    task_type: str,
    token: str,
    file_url: str = "",
    model_version: str = "vlm",
    language: str = "ch",
    is_ocr: bool = False,
    enable_formula: bool = True,
    enable_table: bool = True,
    local_file_path: Optional[str] = None,
    extra_formats: Optional[List[str]] = None,
    page_ranges: Optional[str] = None,
    no_cache: bool = False,
):
    """Spawn task runner in a thread executor."""
    _capture_main_loop()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        run_mineru_task,
        db_id,
        task_type,
        token,
        file_url,
        model_version,
        language,
        is_ocr,
        enable_formula,
        enable_table,
        local_file_path,
        extra_formats,
        page_ranges,
        no_cache,
    )
