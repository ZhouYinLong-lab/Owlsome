from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import db
from app.db import get_connection, init_db
from app.models import (
    ContributionCreateFromPersonalPoint,
    ContributionReviewRequest,
    ExerciseAttemptCreate,
    ExerciseCreate,
    ExerciseLinkRequest,
    NoteCreate,
)
from app.pipelines.importer import SAMPLE_MARKDOWN, import_sample
from app.services import contributions
from app.services import exercises as exercise_service
from app.services.notes import approve_note, create_note
from app.services.personal import create_space_from_sample, get_space, update_progress


PENDING_TITLE = "演示待审核贡献：点集基本知识补充"
APPROVED_TITLE = "演示已合并贡献：多元函数概念补充"
APPROVED_COMMENT = "演示数据：审核通过并合并到公共知识库。"
PENDING_NOTE_TITLE = "演示待审核笔记：二重极限路径提醒"
APPROVED_NOTE_TITLE = "演示已合并笔记：偏导数学习补充"
DEMO_EXERCISE_TITLE = "演示练习：二重极限路径判断"
DEMO_ATTEMPT_NOTE = "演示数据：学习者把这题标记为做错，用于工作台薄弱点展示。"


def backup_and_reset_db() -> Path | None:
    # Seed reset is intentionally scoped to the SQLite runtime files only.
    # It never touches MinerU outputs, uploaded materials, .env files, or source code.
    db.DATA_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if db.DB_PATH.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db.DB_PATH.with_name(f"learning_platform_{timestamp}.db.bak")
        shutil.copy2(db.DB_PATH, backup_path)
    for path in [db.DB_PATH, db.DB_PATH.with_suffix(".db-wal"), db.DB_PATH.with_suffix(".db-shm")]:
        if path.exists():
            try:
                path.unlink()
            except PermissionError as exc:
                raise RuntimeError(
                    "无法重置 SQLite 数据库，文件正在被后端或其他程序占用。"
                    "请先停止 uvicorn / 关闭占用数据库的进程，再重新运行 "
                    "`python scripts\\seed_demo.py --all`。"
                ) from exc
    init_db()
    return backup_path


def ensure_sample_import() -> dict:
    result = import_sample()
    return result.model_dump() if hasattr(result, "model_dump") else result.dict()


def latest_sample_space() -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM personal_spaces
            WHERE source_type = 'sample_markdown'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    return get_space(int(row["id"])) if row else None


def ensure_personal_space() -> dict:
    # Reuse the latest sample space so partial commands can be run repeatedly
    # without filling the demo with identical personal workspaces.
    space = latest_sample_space()
    if space:
        return space
    result = create_space_from_sample()
    space = get_space(int(result["space_id"]))
    if not space:
        raise RuntimeError("个人样例空间创建失败。")
    return space


def contribution_by_title(title: str, status: str | None = None) -> dict | None:
    with get_connection() as conn:
        if status:
            row = conn.execute(
                "SELECT id FROM contributions WHERE title = ? AND status = ? ORDER BY id DESC LIMIT 1",
                (title, status),
            ).fetchone()
        else:
            row = conn.execute("SELECT id FROM contributions WHERE title = ? ORDER BY id DESC LIMIT 1", (title,)).fetchone()
    return contributions.get_contribution(int(row["id"])) if row else None


def ensure_contribution(title: str, point_index: int, approve: bool) -> dict:
    # Demo contributions are idempotent by title and final status. This keeps
    # --all stable while still allowing a reset to rebuild the same story line.
    existing = contribution_by_title(title, "approved" if approve else "pending")
    if existing:
        return existing

    ensure_sample_import()
    space = ensure_personal_space()
    points = space.get("points") or []
    if len(points) <= point_index:
        raise RuntimeError(f"个人样例空间知识点不足，无法取第 {point_index + 1} 个知识点。")

    created = contributions.create_from_personal_point(
        ContributionCreateFromPersonalPoint(
            space_id=int(space["id"]),
            personal_knowledge_point_id=int(points[point_index]["id"]),
            contribution_type="note",
            title=title,
            content_scope="whole_point",
        )
    )
    if approve:
        approved = contributions.approve(int(created["id"]), ContributionReviewRequest(comment=APPROVED_COMMENT))
        if not approved:
            raise RuntimeError("演示贡献审核通过失败。")
        return approved
    return created


def knowledge_point_by_code(code: str) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM knowledge_points WHERE code = ? ORDER BY id LIMIT 1", (code,)).fetchone()
        if row:
            return dict(row)
        fallback = conn.execute("SELECT * FROM knowledge_points ORDER BY id LIMIT 1").fetchone()
    if not fallback:
        raise RuntimeError("公共知识库为空，无法准备演示数据。")
    return dict(fallback)


def note_by_title(title: str, status: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM notes WHERE title = ? AND status = ? ORDER BY id DESC LIMIT 1",
            (title, status),
        ).fetchone()
    return dict(row) if row else None


def ensure_demo_note(title: str, target_code: str, approve: bool) -> dict:
    existing = note_by_title(title, "approved" if approve else "pending")
    if existing:
        return existing

    target = knowledge_point_by_code(target_code)
    created = create_note(
        NoteCreate(
            title=title,
            content=(
                "课堂补充：判断多元函数极限或偏导问题时，要同时关注定义、路径、"
                "变量是否独立趋近，以及计算结果能否脱离路径选择。"
            ),
            knowledge_point_id=int(target["id"]),
            note_type="student_note",
        )
    )
    if approve:
        approved = approve_note(int(created["id"]))
        if not approved:
            raise RuntimeError("演示笔记审核通过失败。")
        return approved
    return created


def ensure_learning_progress(space: dict) -> None:
    points = space.get("points") or []
    planned_statuses = ["mastered", "learning", "difficult"]
    for index, status in enumerate(planned_statuses):
        if len(points) <= index:
            return
        update_progress(int(space["id"]), int(points[index]["id"]), status)


def exercise_by_title(title: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM exercises WHERE title = ? ORDER BY id DESC LIMIT 1", (title,)).fetchone()
    return dict(row) if row else None


def ensure_exercise_loop() -> dict:
    target = knowledge_point_by_code("5.1.3")
    exercise = exercise_by_title(DEMO_EXERCISE_TITLE)
    if not exercise:
        exercise = exercise_service.create_exercise(
            ExerciseCreate(
                title=DEMO_EXERCISE_TITLE,
                stem=(
                    "设二元函数 f(x,y) 在点 (0,0) 附近有定义。若沿直线 y=kx 趋近时"
                    "极限结果随 k 改变，能否说明二重极限存在？为什么？"
                ),
                answer="不能。二重极限要求沿任意路径趋近时都得到同一个结果，只检查直线路径并不充分。",
                analysis="当不同路径或不同斜率直线得到不同极限时，可直接判定二重极限不存在。",
                difficulty=2,
                source="demo_seed",
            )
        )

    exercise_service.link_exercise(
        int(exercise["id"]),
        ExerciseLinkRequest(
            knowledge_point_id=int(target["id"]),
            confidence=1.0,
            reason="演示数据：与二重极限路径判断直接相关。",
        ),
    )

    with get_connection() as conn:
        existing_attempt = conn.execute(
            """
            SELECT id
            FROM exercise_attempts
            WHERE exercise_id = ? AND knowledge_point_id = ? AND result = 'wrong' AND note = ?
            LIMIT 1
            """,
            (int(exercise["id"]), int(target["id"]), DEMO_ATTEMPT_NOTE),
        ).fetchone()
    if not existing_attempt:
        exercise_service.create_attempt(
            int(exercise["id"]),
            ExerciseAttemptCreate(
                knowledge_point_id=int(target["id"]),
                result="wrong",
                note=DEMO_ATTEMPT_NOTE,
            ),
        )
    return exercise


def collect_stats(personal_space_id: int | None, backup_path: Path | None) -> dict:
    with get_connection() as conn:
        stats = {
            "database_path": str(db.DB_PATH),
            "backup_path": str(backup_path) if backup_path else "无",
            "sample_source": str(SAMPLE_MARKDOWN),
            "courses": conn.execute("SELECT COUNT(*) AS count FROM courses").fetchone()["count"],
            "knowledge_points": conn.execute("SELECT COUNT(*) AS count FROM knowledge_points").fetchone()["count"],
            "content_units": conn.execute("SELECT COUNT(*) AS count FROM content_units").fetchone()["count"],
            "personal_space_id": personal_space_id or "无",
            "pending_notes": conn.execute("SELECT COUNT(*) AS count FROM notes WHERE status = 'pending'").fetchone()["count"],
            "approved_notes": conn.execute("SELECT COUNT(*) AS count FROM notes WHERE status = 'approved'").fetchone()["count"],
            "pending_contributions": conn.execute(
                "SELECT COUNT(*) AS count FROM contributions WHERE status = 'pending'"
            ).fetchone()["count"],
            "approved_contributions": conn.execute(
                "SELECT COUNT(*) AS count FROM contributions WHERE status = 'approved'"
            ).fetchone()["count"],
            "community_content_units": conn.execute(
                "SELECT COUNT(*) AS count FROM content_units WHERE source LIKE 'community_contribution:%'"
            ).fetchone()["count"],
            "exercises": conn.execute("SELECT COUNT(*) AS count FROM exercises").fetchone()["count"],
            "linked_exercises": conn.execute("SELECT COUNT(*) AS count FROM exercises WHERE status = 'linked'").fetchone()["count"],
            "exercise_attempts": conn.execute("SELECT COUNT(*) AS count FROM exercise_attempts").fetchone()["count"],
            "mistake_attempts": conn.execute(
                "SELECT COUNT(*) AS count FROM exercise_attempts WHERE result = 'wrong'"
            ).fetchone()["count"],
            "weak_knowledge_points": conn.execute(
                "SELECT COUNT(DISTINCT knowledge_point_id) AS count FROM exercise_attempts WHERE result IN ('wrong', 'unsure') AND knowledge_point_id IS NOT NULL"
            ).fetchone()["count"],
        }
    return stats


def print_stats(stats: dict) -> None:
    print("\nDemo seed 完成")
    print("=" * 48)
    labels = [
        ("数据库路径", "database_path"),
        ("备份路径", "backup_path"),
        ("导入源", "sample_source"),
        ("课程数", "courses"),
        ("知识点数量", "knowledge_points"),
        ("内容单元数量", "content_units"),
        ("个人空间 ID", "personal_space_id"),
        ("pending 笔记数", "pending_notes"),
        ("approved 笔记数", "approved_notes"),
        ("pending 贡献数", "pending_contributions"),
        ("approved 贡献数", "approved_contributions"),
        ("社区内容数", "community_content_units"),
        ("题目数", "exercises"),
        ("已绑定题目数", "linked_exercises"),
        ("练习记录数", "exercise_attempts"),
        ("错题记录数", "mistake_attempts"),
        ("薄弱知识点数", "weak_knowledge_points"),
    ]
    for label, key in labels:
        print(f"{label}: {stats[key]}")
    print("\n推荐演示步骤:")
    print("1. 启动后端: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload")
    print(f"2. 启动前端: cd {BACKEND_DIR.parent / 'frontend'}; npm run dev")
    print("3. 打开: http://127.0.0.1:5173")
    print("4. 查看工作台、公共知识库、个人学习空间、审核中心、练习与薄弱点。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare reproducible Owlsome Learning demo data.")
    parser.add_argument("--reset", action="store_true", help="备份并重置 SQLite 数据库")
    parser.add_argument("--import-sample", action="store_true", help="导入清洗版教材样例")
    parser.add_argument("--personal-space", action="store_true", help="创建个人样例空间")
    parser.add_argument("--learning-progress", action="store_true", help="设置个人空间进度样例")
    parser.add_argument("--pending-note", action="store_true", help="创建一条待审核笔记")
    parser.add_argument("--approved-note", action="store_true", help="创建并审核通过一条公共笔记")
    parser.add_argument("--pending-contribution", action="store_true", help="创建一条待审核贡献")
    parser.add_argument("--approved-contribution", action="store_true", help="创建并审核通过一条社区贡献")
    parser.add_argument("--exercise-loop", action="store_true", help="创建题目绑定与错题薄弱点样例")
    parser.add_argument("--all", action="store_true", help="执行完整演示准备")
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.error("请至少指定一个参数，例如 --all。")

    if args.all:
        args.reset = True
        args.import_sample = True
        args.personal_space = True
        args.learning_progress = True
        args.pending_note = True
        args.approved_note = True
        args.pending_contribution = True
        args.approved_contribution = True
        args.exercise_loop = True

    backup_path = None
    personal_space_id = None

    if args.reset:
        backup_path = backup_and_reset_db()
    else:
        init_db()

    if (
        args.import_sample
        or args.personal_space
        or args.learning_progress
        or args.pending_note
        or args.approved_note
        or args.pending_contribution
        or args.approved_contribution
        or args.exercise_loop
    ):
        ensure_sample_import()

    if args.personal_space or args.learning_progress or args.pending_contribution or args.approved_contribution:
        space = ensure_personal_space()
        personal_space_id = int(space["id"])

    if args.learning_progress:
        space = ensure_personal_space()
        personal_space_id = int(space["id"])
        ensure_learning_progress(space)

    if args.pending_note:
        ensure_demo_note(PENDING_NOTE_TITLE, target_code="5.1.3", approve=False)

    if args.approved_note:
        ensure_demo_note(APPROVED_NOTE_TITLE, target_code="5.2.1", approve=True)

    if args.pending_contribution:
        ensure_contribution(PENDING_TITLE, point_index=0, approve=False)

    if args.approved_contribution:
        ensure_contribution(APPROVED_TITLE, point_index=1, approve=True)

    if args.exercise_loop:
        ensure_exercise_loop()

    if not personal_space_id:
        space = latest_sample_space()
        personal_space_id = int(space["id"]) if space else None

    print_stats(collect_stats(personal_space_id, backup_path))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"\nDemo seed 失败：{exc}", file=sys.stderr)
        sys.exit(1)
