"""
MinerU WebUI — FastAPI Application.

Features:
  - URL parse (precision & agent API)
  - Local file upload → batch upload pipeline
  - Large PDF auto-split & merge
  - Real-time SSE progress tracking
  - Task history & management
"""

import asyncio
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, File, UploadFile, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import db
from . import task_manager as tm

# ── App Setup ──

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
UPLOAD_DIR = BASE_DIR.parent / "uploads"
OUTPUT_DIR = BASE_DIR.parent / "output"

os.makedirs(str(UPLOAD_DIR), exist_ok=True)
os.makedirs(str(OUTPUT_DIR), exist_ok=True)

app = FastAPI(title="MinerU WebUI", version="1.0.0")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 environment (bypass Starlette compat issue)
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)
_jinja_env.globals["enumerate"] = enumerate


def render_template(name: str, request: Request, **context) -> HTMLResponse:
    """Render a Jinja2 template with request context."""
    context["request"] = request
    tmpl = _jinja_env.get_template(name)
    return HTMLResponse(tmpl.render(**context))


# ── Startup ──

@app.on_event("startup")
async def startup():
    await db.init_db()


# ── Configuration helper ──

def _get_config_path() -> Path:
    return BASE_DIR.parent / "config.json"


def read_config() -> dict:
    cfg_path = _get_config_path()
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return {}


def save_config(cfg: dict):
    _get_config_path().write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Routes: Pages ──

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    stats = await db.get_stats()
    recent = await db.list_tasks(limit=10)
    config = read_config()
    return render_template("index.html",
        request=request,
        stats=stats,
        recent_tasks=recent,
        config=config,
    )


@app.get("/tasks/new", response_class=HTMLResponse)
async def new_task_page(request: Request):
    config = read_config()
    return render_template("new_task.html",
        request=request,
        config=config,
    )


@app.get("/tasks/{db_id}", response_class=HTMLResponse)
async def task_detail_page(request: Request, db_id: int):
    task = await db.get_task(db_id)
    if not task:
        return HTMLResponse("Task not found", status_code=404)
    return render_template("task_detail.html",
        request=request,
        task=task,
    )


@app.get("/history", response_class=HTMLResponse)
async def history_page(
    request: Request,
    state: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
):
    per_page = 30
    offset = (page - 1) * per_page
    tasks = await db.list_tasks(state=state, limit=per_page, offset=offset)
    stats = await db.get_stats()
    return render_template("history.html",
        request=request,
        tasks=tasks,
        stats=stats,
        current_state=state or "",
        page=page,
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    config = read_config()
    return render_template("settings.html",
        request=request,
        config=config,
    )


# ── Routes: API ──

@app.post("/api/settings")
async def save_settings(
    token: str = Form(""),
    default_model: str = Form("vlm"),
    default_language: str = Form("ch"),
    requests_per_second: float = Form(3.0),
    task_timeout: int = Form(600),
):
    cfg = {
        "token": token,
        "default_model": default_model,
        "default_language": default_language,
        "requests_per_second": requests_per_second,
        "task_timeout": task_timeout,
    }
    save_config(cfg)
    return JSONResponse({"ok": True})


@app.post("/api/tasks")
async def create_task(
    task_type: str = Form(...),
    file_url: str = Form(""),
    model_version: str = Form("vlm"),
    language: str = Form("ch"),
    is_ocr: bool = Form(False),
    enable_formula: bool = Form(True),
    enable_table: bool = Form(True),
    page_ranges: str = Form(""),
    no_cache: bool = Form(False),
    extra_formats: str = Form(""),
    pdf_file: Optional[UploadFile] = File(None),
):
    config = read_config()
    token = config.get("token", "")

    if task_type in ("precision", "agent") and not file_url and not pdf_file:
        return JSONResponse({"error": "Either file URL or PDF file is required"}, status_code=400)

    if task_type in ("precision", "precision_file") and not token:
        return JSONResponse({"error": "API token is required for precision API. Set it in Settings."}, status_code=400)

    # Handle file upload
    local_path = None
    effective_url = file_url
    effective_file_name = file_url.rsplit("/", 1)[-1].split("?")[0] if file_url else ""

    if pdf_file:
        effective_file_name = pdf_file.filename or "upload.pdf"
        local_path = str(UPLOAD_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{effective_file_name}")
        with open(local_path, "wb") as f:
            content = await pdf_file.read()
            f.write(content)
        effective_url = f"file://{local_path}"
        if task_type == "agent":
            task_type = "agent_file"
        else:
            task_type = "precision_file"

    # Parse extra_formats
    ef_list = [f.strip() for f in extra_formats.split(",") if f.strip()] if extra_formats else None

    db_id = await db.save_task({
        "task_id": "",
        "file_name": effective_file_name,
        "file_url": effective_url,
        "state": "pending",
        "task_type": task_type,
        "model_version": model_version,
        "language": language,
        "is_ocr": 1 if is_ocr else 0,
        "enable_formula": 1 if enable_formula else 0,
        "enable_table": 1 if enable_table else 0,
        "params_json": json.dumps({
            "page_ranges": page_ranges,
            "no_cache": no_cache,
            "extra_formats": ef_list,
        }, ensure_ascii=False),
        "metadata_json": json.dumps({"local_file_path": local_path} if local_path else {}, ensure_ascii=False),
    })

    # Start background task with error logging
    async def _launch():
        try:
            await tm.start_task_in_background(
                db_id=db_id,
                task_type=task_type,
                token=token,
                file_url=file_url if task_type not in ("precision_file", "agent_file") else "",
                model_version=model_version,
                language=language,
                is_ocr=is_ocr,
                enable_formula=enable_formula,
                enable_table=enable_table,
                local_file_path=local_path,
                extra_formats=ef_list,
                page_ranges=page_ranges or None,
                no_cache=no_cache,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Background task %d failed to start", db_id)
            from .task_manager import emit_event, SSEEvent
            emit_event(SSEEvent(db_id=db_id, event="error",
                data={"error": f"Failed to start: {e}", "code": "StartupError"}))

    asyncio.create_task(_launch())

    return JSONResponse({"ok": True, "db_id": db_id})


@app.get("/api/tasks/{db_id}")
async def get_task_info(db_id: int):
    task = await db.get_task(db_id)
    if not task:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(task)


@app.delete("/api/tasks/{db_id}")
async def delete_task_api(db_id: int):
    task = await db.get_task(db_id)
    if not task:
        return JSONResponse({"error": "Not found"}, status_code=404)
    # Clean up output files
    if task.get("local_output_dir"):
        try:
            shutil.rmtree(task["local_output_dir"], ignore_errors=True)
        except Exception:
            pass
    metadata = json.loads(task.get("metadata_json", "{}"))
    if metadata.get("local_file_path"):
        try:
            os.remove(metadata["local_file_path"])
        except Exception:
            pass
    await db.delete_task(db_id)
    return JSONResponse({"ok": True})


@app.get("/api/tasks/{db_id}/sse")
async def task_sse(db_id: int):
    """Server-Sent Events stream for real-time task progress."""
    task = await db.get_task(db_id)
    if not task:
        return JSONResponse({"error": "Not found"}, status_code=404)

    return StreamingResponse(
        tm.sse_stream(db_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/tasks/{db_id}/markdown")
async def get_task_markdown(db_id: int):
    task = await db.get_task(db_id)
    if not task:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse({"markdown_content": task.get("markdown_content", "")})


@app.get("/api/stats")
async def get_stats():
    return JSONResponse(await db.get_stats())


@app.post("/api/settings/clear-output")
async def clear_output():
    import shutil
    if OUTPUT_DIR.exists():
        shutil.rmtree(str(OUTPUT_DIR), ignore_errors=True)
        os.makedirs(str(OUTPUT_DIR), exist_ok=True)
    return JSONResponse({"ok": True})


@app.post("/api/settings/clear-uploads")
async def clear_uploads():
    import shutil
    if UPLOAD_DIR.exists():
        shutil.rmtree(str(UPLOAD_DIR), ignore_errors=True)
        os.makedirs(str(UPLOAD_DIR), exist_ok=True)
    return JSONResponse({"ok": True})


@app.get("/output/{path:path}")
async def serve_output(path: str):
    """Serve downloaded output files (markdown, etc)."""
    full_path = OUTPUT_DIR / path
    if not full_path.exists():
        return HTMLResponse("File not found", status_code=404)
    if full_path.suffix == ".md":
        return HTMLResponse(full_path.read_text(encoding="utf-8"), media_type="text/plain; charset=utf-8")
    from fastapi.responses import FileResponse
    return FileResponse(str(full_path))
