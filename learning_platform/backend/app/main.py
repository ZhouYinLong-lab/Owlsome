from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_connection, init_db, row_to_dict, rows_to_dicts
from app.models import (
    CalculusFullImportRequest,
    CalculusFullImportResult,
    ContributionCreateFromPersonalPoint,
    ContributionReviewRequest,
    ExerciseAttemptCreate,
    ExerciseCreate,
    ExerciseLinkRequest,
    ExerciseRecommendRequest,
    ImportResult,
    NoteCreate,
    PersonalProgressUpdate,
    PersonalQARequest,
    QARequest,
    QAResponse,
)
from app.pipelines.calculus_full_importer import import_calculus_full
from app.pipelines.importer import import_sample
from app.services import contributions
from app.services import exercises as exercise_service
from app.services.notes import approve_note, create_note, pending_notes, reject_note
from app.services.personal import (
    create_space_from_markdown_bytes,
    create_space_from_sample,
    get_personal_point,
    get_space,
    list_spaces,
    update_progress,
)
from app.services.qa import answer_personal_question, answer_question


app = FastAPI(title="AI 交互式数学学习平台 Demo", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    # Vite 在 5173 被占用时会自动切到 5174/5175。
    # Demo 常在本机不同端口间切换，因此允许 localhost/127.0.0.1 的任意端口。
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TestClient 在某些版本中不进入 lifespan context 时也要可用；真实 uvicorn
# 启动时下面的 startup 事件会再执行一次，SQLite 的 CREATE IF NOT EXISTS 是幂等的。
init_db()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "learning_platform"}


@app.get("/api/stats")
def stats() -> dict:
    with get_connection() as conn:
        return {
            "courses": conn.execute("SELECT COUNT(*) AS count FROM courses").fetchone()["count"],
            "knowledge_points": conn.execute("SELECT COUNT(*) AS count FROM knowledge_points").fetchone()["count"],
            "content_units": conn.execute("SELECT COUNT(*) AS count FROM content_units").fetchone()["count"],
            "pending_notes": conn.execute("SELECT COUNT(*) AS count FROM notes WHERE status = 'pending'").fetchone()["count"],
            "approved_notes": conn.execute("SELECT COUNT(*) AS count FROM notes WHERE status = 'approved'").fetchone()["count"],
            "qa_logs": conn.execute("SELECT COUNT(*) AS count FROM qa_logs").fetchone()["count"],
            "personal_spaces": conn.execute("SELECT COUNT(*) AS count FROM personal_spaces").fetchone()["count"],
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
        }


@app.post("/api/import/sample", response_model=ImportResult)
def import_sample_api() -> ImportResult:
    try:
        return import_sample()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/import/calculus-full", response_model=CalculusFullImportResult)
def import_calculus_full_api(payload: CalculusFullImportRequest | None = None) -> dict:
    options = payload or CalculusFullImportRequest()
    try:
        return import_calculus_full(
            dry_run=options.dry_run,
            reset_course_before_import=options.reset_course,
            write_report_file=options.write_report,
            via_api=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/courses")
def courses() -> list[dict]:
    with get_connection() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM courses ORDER BY id").fetchall())


@app.get("/api/knowledge-points")
def knowledge_points() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                kp.*,
                COUNT(DISTINCT cu.id) AS content_count,
                COUNT(DISTINCT n.id) AS approved_note_count,
                c.title AS chapter_title
            FROM knowledge_points kp
            JOIN chapters c ON c.id = kp.chapter_id
            LEFT JOIN content_units cu ON cu.knowledge_point_id = kp.id
            LEFT JOIN notes n ON n.knowledge_point_id = kp.id AND n.status = 'approved'
            GROUP BY kp.id
            ORDER BY c.order_index, kp.order_index
            """
        ).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/knowledge-points/{knowledge_point_id}")
def knowledge_point_detail(knowledge_point_id: int) -> dict:
    with get_connection() as conn:
        point = row_to_dict(
            conn.execute(
                """
                SELECT
                    kp.*,
                    c.title AS chapter_title,
                    cr.name AS course_name
                FROM knowledge_points kp
                JOIN chapters c ON c.id = kp.chapter_id
                JOIN courses cr ON cr.id = c.course_id
                WHERE kp.id = ?
                """,
                (knowledge_point_id,),
            ).fetchone()
        )
        if not point:
            raise HTTPException(status_code=404, detail="知识点不存在")
        point["units"] = rows_to_dicts(
            conn.execute(
                "SELECT * FROM content_units WHERE knowledge_point_id = ? ORDER BY order_index",
                (knowledge_point_id,),
            ).fetchall()
        )
        point["notes"] = rows_to_dicts(
            conn.execute(
                "SELECT * FROM notes WHERE knowledge_point_id = ? AND status = 'approved' ORDER BY reviewed_at DESC",
                (knowledge_point_id,),
            ).fetchall()
        )
    return point


@app.post("/api/notes")
def create_note_api(payload: NoteCreate) -> dict:
    return create_note(payload)


@app.get("/api/notes/pending")
def pending_notes_api() -> list[dict]:
    return pending_notes()


@app.post("/api/notes/{note_id}/approve")
def approve_note_api(note_id: int) -> dict:
    note = approve_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


@app.post("/api/notes/{note_id}/reject")
def reject_note_api(note_id: int) -> dict:
    note = reject_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


@app.post("/api/qa", response_model=QAResponse)
def qa_api(payload: QARequest) -> dict:
    try:
        return answer_question(payload.knowledge_point_id, payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/personal-spaces/upload-markdown")
async def upload_personal_markdown(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    try:
        return create_space_from_markdown_bytes(file.filename or "upload.md", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/personal-spaces/from-sample")
def personal_space_from_sample_api() -> dict:
    try:
        return create_space_from_sample()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/personal-spaces")
def personal_spaces_api() -> list[dict]:
    return list_spaces()


@app.get("/api/personal-spaces/{space_id}")
def personal_space_api(space_id: int) -> dict:
    space = get_space(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="个人学习空间不存在")
    return space


@app.get("/api/personal-spaces/{space_id}/knowledge-points/{point_id}")
def personal_knowledge_point_api(space_id: int, point_id: int) -> dict:
    point = get_personal_point(space_id, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="个人知识点不存在")
    return point


@app.post("/api/personal-spaces/{space_id}/knowledge-points/{point_id}/progress")
def personal_progress_api(space_id: int, point_id: int, payload: PersonalProgressUpdate) -> dict:
    try:
        point = update_progress(space_id, point_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not point:
        raise HTTPException(status_code=404, detail="个人知识点不存在")
    return point


@app.post("/api/personal-spaces/{space_id}/qa", response_model=QAResponse)
def personal_qa_api(space_id: int, payload: PersonalQARequest) -> dict:
    try:
        return answer_personal_question(space_id, payload.personal_knowledge_point_id, payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/contributions/from-personal-point")
def create_contribution_api(payload: ContributionCreateFromPersonalPoint) -> dict:
    try:
        return contributions.create_from_personal_point(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/contributions/pending")
def pending_contributions_api() -> list[dict]:
    return contributions.list_pending()


@app.get("/api/contributions/{contribution_id}")
def contribution_detail_api(contribution_id: int) -> dict:
    contribution = contributions.get_contribution(contribution_id)
    if not contribution:
        raise HTTPException(status_code=404, detail="贡献不存在")
    return contribution


@app.post("/api/contributions/{contribution_id}/approve")
def approve_contribution_api(contribution_id: int, payload: ContributionReviewRequest) -> dict:
    try:
        contribution = contributions.approve(contribution_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not contribution:
        raise HTTPException(status_code=404, detail="贡献不存在")
    return contribution


@app.post("/api/contributions/{contribution_id}/reject")
def reject_contribution_api(contribution_id: int, payload: ContributionReviewRequest) -> dict:
    try:
        contribution = contributions.reject(contribution_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not contribution:
        raise HTTPException(status_code=404, detail="贡献不存在")
    return contribution


@app.post("/api/contributions/{contribution_id}/request-revision")
def request_revision_contribution_api(contribution_id: int, payload: ContributionReviewRequest) -> dict:
    try:
        contribution = contributions.request_revision(contribution_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not contribution:
        raise HTTPException(status_code=404, detail="贡献不存在")
    return contribution


# ── Exercise endpoints ──────────────────────────────────────────

@app.post("/api/exercises")
def create_exercise_api(payload: ExerciseCreate) -> dict:
    return exercise_service.create_exercise(payload)


@app.get("/api/exercises")
def list_exercises_api() -> list[dict]:
    return exercise_service.list_exercises()


@app.get("/api/exercises/{exercise_id}")
def get_exercise_api(exercise_id: int) -> dict:
    exercise = exercise_service.get_exercise(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="题目不存在")
    return exercise


@app.post("/api/exercises/recommend")
def recommend_exercise_api(payload: ExerciseRecommendRequest) -> dict:
    try:
        result = exercise_service.recommend_knowledge_points(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.model_dump()


@app.post("/api/exercises/{exercise_id}/link")
def link_exercise_api(exercise_id: int, payload: ExerciseLinkRequest) -> dict:
    try:
        return exercise_service.link_exercise(exercise_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/knowledge-points/{knowledge_point_id}/exercises")
def knowledge_point_exercises_api(knowledge_point_id: int) -> list[dict]:
    return exercise_service.list_exercises_for_knowledge_point(knowledge_point_id)


@app.post("/api/exercises/{exercise_id}/attempts")
def create_attempt_api(exercise_id: int, payload: ExerciseAttemptCreate) -> dict:
    try:
        return exercise_service.create_attempt(exercise_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
