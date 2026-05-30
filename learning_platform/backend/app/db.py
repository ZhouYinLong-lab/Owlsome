from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "learning_platform.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row objects for dict-like API responses."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all MVP tables. The schema is intentionally small and demo-friendly."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                order_index INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
                UNIQUE(course_id, title)
            );

            CREATE TABLE IF NOT EXISTS knowledge_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                raw_markdown TEXT NOT NULL DEFAULT '',
                order_index INTEGER NOT NULL DEFAULT 0,
                difficulty INTEGER NOT NULL DEFAULT 1,
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
                UNIQUE(chapter_id, code)
            );

            CREATE TABLE IF NOT EXISTS content_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_point_id INTEGER NOT NULL,
                unit_type TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                order_index INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_point_id INTEGER,
                matched_knowledge_point_id INTEGER,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                note_type TEXT NOT NULL DEFAULT 'student_note',
                status TEXT NOT NULL DEFAULT 'pending',
                match_reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                FOREIGN KEY(knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE SET NULL,
                FOREIGN KEY(matched_knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS qa_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_point_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'offline',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS personal_spaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source_file TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'markdown',
                status TEXT NOT NULL DEFAULT 'ready',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS personal_knowledge_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                space_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                raw_markdown TEXT NOT NULL DEFAULT '',
                order_index INTEGER NOT NULL DEFAULT 0,
                difficulty INTEGER NOT NULL DEFAULT 1,
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(space_id) REFERENCES personal_spaces(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS personal_content_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personal_knowledge_point_id INTEGER NOT NULL,
                unit_type TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                order_index INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(personal_knowledge_point_id) REFERENCES personal_knowledge_points(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS learning_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                space_id INTEGER NOT NULL,
                personal_knowledge_point_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'not_started',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(space_id) REFERENCES personal_spaces(id) ON DELETE CASCADE,
                FOREIGN KEY(personal_knowledge_point_id) REFERENCES personal_knowledge_points(id) ON DELETE CASCADE,
                UNIQUE(space_id, personal_knowledge_point_id)
            );

            CREATE TABLE IF NOT EXISTS contributors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handle TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contributor_id INTEGER NOT NULL,
                source_space_id INTEGER,
                source_personal_point_id INTEGER,
                recommended_knowledge_point_id INTEGER,
                target_knowledge_point_id INTEGER,
                contribution_type TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content_scope TEXT NOT NULL DEFAULT 'whole_point',
                status TEXT NOT NULL DEFAULT 'pending',
                match_reason TEXT NOT NULL DEFAULT '',
                duplicate_risk TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,
                FOREIGN KEY(contributor_id) REFERENCES contributors(id) ON DELETE CASCADE,
                FOREIGN KEY(source_space_id) REFERENCES personal_spaces(id) ON DELETE SET NULL,
                FOREIGN KEY(source_personal_point_id) REFERENCES personal_knowledge_points(id) ON DELETE SET NULL,
                FOREIGN KEY(recommended_knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE SET NULL,
                FOREIGN KEY(target_knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS contribution_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contribution_id INTEGER NOT NULL,
                unit_type TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL,
                order_index INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(contribution_id) REFERENCES contributions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS contribution_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contribution_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                reviewer TEXT NOT NULL DEFAULT 'local_reviewer',
                comment TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(contribution_id) REFERENCES contributions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '',
                stem TEXT NOT NULL,
                answer TEXT NOT NULL DEFAULT '',
                analysis TEXT NOT NULL DEFAULT '',
                exercise_type TEXT NOT NULL DEFAULT 'practice',
                difficulty INTEGER NOT NULL DEFAULT 2,
                source TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS exercise_knowledge_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER NOT NULL,
                knowledge_point_id INTEGER NOT NULL,
                confidence REAL NOT NULL DEFAULT 0,
                reason TEXT NOT NULL DEFAULT '',
                confirmed_by TEXT NOT NULL DEFAULT 'local_admin',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
                FOREIGN KEY(knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE CASCADE,
                UNIQUE(exercise_id, knowledge_point_id)
            );

            CREATE TABLE IF NOT EXISTS exercise_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_id INTEGER NOT NULL,
                knowledge_point_id INTEGER,
                result TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(exercise_id) REFERENCES exercises(id) ON DELETE CASCADE,
                FOREIGN KEY(knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE SET NULL
            );
            """
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO contributors (handle, display_name)
            VALUES ('local_demo_user', '本地演示用户')
            """
        )


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None
