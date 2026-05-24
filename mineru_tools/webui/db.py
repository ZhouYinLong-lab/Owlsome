"""
Task persistence layer — async SQLite via aiosqlite.
"""

import aiosqlite
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "tasks.db"


async def get_db() -> aiosqlite.Connection:
    os.makedirs(str(DB_DIR), exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            file_name TEXT NOT NULL DEFAULT '',
            file_url TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'pending',
            task_type TEXT NOT NULL DEFAULT 'precision',
            model_version TEXT NOT NULL DEFAULT 'vlm',
            language TEXT NOT NULL DEFAULT 'ch',
            is_ocr INTEGER NOT NULL DEFAULT 0,
            enable_formula INTEGER NOT NULL DEFAULT 1,
            enable_table INTEGER NOT NULL DEFAULT 1,
            error_msg TEXT NOT NULL DEFAULT '',
            full_zip_url TEXT NOT NULL DEFAULT '',
            local_output_dir TEXT NOT NULL DEFAULT '',
            markdown_content TEXT NOT NULL DEFAULT '',
            progress_pages INTEGER NOT NULL DEFAULT 0,
            total_pages INTEGER NOT NULL DEFAULT 0,
            batch_total INTEGER NOT NULL DEFAULT 0,
            batch_completed INTEGER NOT NULL DEFAULT 0,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            chunk_total INTEGER NOT NULL DEFAULT 0,
            params_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
        CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);
    """)
    await db.commit()
    await db.close()


_DEFAULTS = {
    "task_id": "", "file_name": "", "file_url": "", "state": "pending",
    "task_type": "precision", "model_version": "vlm", "language": "ch",
    "is_ocr": 0, "enable_formula": 1, "enable_table": 1,
    "error_msg": "", "full_zip_url": "", "local_output_dir": "", "markdown_content": "",
    "progress_pages": 0, "total_pages": 0, "batch_total": 0, "batch_completed": 0,
    "chunk_index": 0, "chunk_total": 0, "params_json": "{}", "metadata_json": "{}",
}

_COLS = [
    "task_id", "file_name", "file_url", "state", "task_type",
    "model_version", "language", "is_ocr", "enable_formula", "enable_table",
    "error_msg", "full_zip_url", "local_output_dir", "markdown_content",
    "progress_pages", "total_pages", "batch_total", "batch_completed",
    "chunk_index", "chunk_total", "params_json", "metadata_json",
    "created_at", "updated_at",
]


async def save_task(task_data: Dict[str, Any]):
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    values = {**_DEFAULTS, **task_data, "created_at": now, "updated_at": now}
    placeholders = ", ".join(f":{c}" for c in _COLS)
    cols = ", ".join(_COLS)
    cursor = await db.execute(f"INSERT INTO tasks ({cols}) VALUES ({placeholders})", values)
    await db.commit()
    last_id = cursor.lastrowid
    await db.close()
    return last_id


async def update_task(db_id: int, updates: Dict[str, Any]):
    if not updates:
        return
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k}=:{k}" for k in updates)
    updates["id"] = db_id
    db = await get_db()
    await db.execute(f"UPDATE tasks SET {set_clause} WHERE id=:id", updates)
    await db.commit()
    await db.close()


async def get_task(db_id: int) -> Optional[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (db_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def get_task_by_task_id(task_id: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tasks WHERE task_id=? ORDER BY id DESC LIMIT 1", (task_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def list_tasks(
    state: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    db = await get_db()
    if state:
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE state=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (state, limit, offset),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM tasks ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_stats() -> Dict[str, int]:
    db = await get_db()
    cursor = await db.execute("""
        SELECT state, COUNT(*) as cnt FROM tasks GROUP BY state
    """)
    rows = await cursor.fetchall()
    await db.close()
    stats = {"total": 0, "pending": 0, "running": 0, "done": 0, "failed": 0}
    for r in rows:
        st = r["state"]
        cnt = r["cnt"]
        stats["total"] += cnt
        if st in stats:
            stats[st] = cnt
    return stats


async def delete_task(db_id: int):
    db = await get_db()
    await db.execute("DELETE FROM tasks WHERE id=?", (db_id,))
    await db.commit()
    await db.close()
