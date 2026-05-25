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
from app.models import ContributionCreateFromPersonalPoint, ContributionReviewRequest
from app.pipelines.importer import SAMPLE_MARKDOWN, import_sample
from app.services import contributions
from app.services.personal import create_space_from_sample, get_space


PENDING_TITLE = "演示待审核贡献：点集基本知识补充"
APPROVED_TITLE = "演示已合并贡献：多元函数概念补充"
APPROVED_COMMENT = "演示数据：审核通过并合并到公共知识库。"


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
            path.unlink()
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
            "pending_contributions": conn.execute(
                "SELECT COUNT(*) AS count FROM contributions WHERE status = 'pending'"
            ).fetchone()["count"],
            "approved_contributions": conn.execute(
                "SELECT COUNT(*) AS count FROM contributions WHERE status = 'approved'"
            ).fetchone()["count"],
            "community_content_units": conn.execute(
                "SELECT COUNT(*) AS count FROM content_units WHERE source LIKE 'community_contribution:%'"
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
        ("pending 贡献数", "pending_contributions"),
        ("approved 贡献数", "approved_contributions"),
        ("社区内容数", "community_content_units"),
    ]
    for label, key in labels:
        print(f"{label}: {stats[key]}")
    print("\n推荐演示步骤:")
    print("1. 启动后端: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload")
    print("2. 启动前端: cd D:\\Projects\\EL\\learning_platform\\frontend; npm run dev")
    print("3. 打开: http://127.0.0.1:5173")
    print("4. 查看控制台统计、公共知识库、个人学习空间和审核中心。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare reproducible Owlsome Learning demo data.")
    parser.add_argument("--reset", action="store_true", help="备份并重置 SQLite 数据库")
    parser.add_argument("--import-sample", action="store_true", help="导入清洗版教材样例")
    parser.add_argument("--personal-space", action="store_true", help="创建个人样例空间")
    parser.add_argument("--pending-contribution", action="store_true", help="创建一条待审核贡献")
    parser.add_argument("--approved-contribution", action="store_true", help="创建并审核通过一条社区贡献")
    parser.add_argument("--all", action="store_true", help="执行完整演示准备")
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.error("请至少指定一个参数，例如 --all。")

    if args.all:
        args.reset = args.import_sample = args.personal_space = args.pending_contribution = args.approved_contribution = True

    backup_path = None
    personal_space_id = None

    if args.reset:
        backup_path = backup_and_reset_db()
    else:
        init_db()

    if args.import_sample or args.personal_space or args.pending_contribution or args.approved_contribution:
        ensure_sample_import()

    if args.personal_space or args.pending_contribution or args.approved_contribution:
        space = ensure_personal_space()
        personal_space_id = int(space["id"])

    if args.pending_contribution:
        ensure_contribution(PENDING_TITLE, point_index=0, approve=False)

    if args.approved_contribution:
        ensure_contribution(APPROVED_TITLE, point_index=1, approve=True)

    if not personal_space_id:
        space = latest_sample_space()
        personal_space_id = int(space["id"]) if space else None

    print_stats(collect_stats(personal_space_id, backup_path))


if __name__ == "__main__":
    main()
