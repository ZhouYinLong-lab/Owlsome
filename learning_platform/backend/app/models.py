from __future__ import annotations

from pydantic import BaseModel, Field


class ImportResult(BaseModel):
    ok: bool
    message: str
    course_id: int | None = None
    chapter_id: int | None = None
    knowledge_points: int = 0
    content_units: int = 0


class CalculusFullImportRequest(BaseModel):
    dry_run: bool = False
    reset_course: bool = False
    write_report: bool = True


class CalculusFullImportResult(BaseModel):
    ok: bool
    message: str
    course_id: int | None = None
    input_path: str
    report_path: str = ""
    imported: bool
    reset_course: bool
    chapters: int
    knowledge_points: int
    content_units: int
    unit_counts: dict[str, int]


class CourseOut(BaseModel):
    id: int
    name: str
    description: str
    source: str


class KnowledgePointOut(BaseModel):
    id: int
    chapter_id: int
    code: str
    title: str
    summary: str
    difficulty: int
    tags: str
    content_count: int = 0
    approved_note_count: int = 0


class ContentUnitOut(BaseModel):
    id: int
    unit_type: str
    title: str
    content: str
    order_index: int
    source: str


class NoteOut(BaseModel):
    id: int
    knowledge_point_id: int | None = None
    matched_knowledge_point_id: int | None = None
    title: str
    content: str
    note_type: str
    status: str
    match_reason: str
    created_at: str


class KnowledgePointDetail(BaseModel):
    id: int
    chapter_id: int
    code: str
    title: str
    summary: str
    raw_markdown: str
    difficulty: int
    tags: str
    units: list[ContentUnitOut]
    notes: list[NoteOut]


class NoteCreate(BaseModel):
    title: str = Field(default="", max_length=120)
    content: str = Field(min_length=2)
    knowledge_point_id: int | None = None
    note_type: str = "student_note"


class QARequest(BaseModel):
    knowledge_point_id: int
    question: str = Field(min_length=2)


class QAResponse(BaseModel):
    answer: str
    mode: str


class PersonalSpaceCreateResult(BaseModel):
    ok: bool
    message: str
    space_id: int
    knowledge_points: int
    content_units: int


class PersonalProgressUpdate(BaseModel):
    status: str = Field(pattern="^(not_started|learning|mastered|difficult)$")


class PersonalQARequest(BaseModel):
    personal_knowledge_point_id: int
    question: str = Field(min_length=2)


class ContributionCreateFromPersonalPoint(BaseModel):
    space_id: int
    personal_knowledge_point_id: int
    contribution_type: str = Field(pattern="^(note|explanation|example|exercise|mistake|faq)$")
    title: str = Field(default="", max_length=160)
    content_scope: str = Field(default="whole_point", pattern="^whole_point$")


class ContributionReviewRequest(BaseModel):
    comment: str = Field(default="", max_length=500)
    target_knowledge_point_id: int | None = None


# ── Exercise models ──────────────────────────────────────────────

class ExerciseCreate(BaseModel):
    title: str = Field(default="", max_length=200)
    stem: str = Field(min_length=2, max_length=8000)
    answer: str = Field(default="", max_length=8000)
    analysis: str = Field(default="", max_length=8000)
    exercise_type: str = Field(default="practice", pattern="^(practice|homework|exam)$")
    difficulty: int = Field(default=2, ge=1, le=5)
    source: str = Field(default="", max_length=200)


class ExerciseRecommendRequest(BaseModel):
    exercise_id: int | None = None
    stem: str | None = None
    top_k: int = Field(default=3, ge=1, le=10)


class ExerciseRecommendCandidate(BaseModel):
    knowledge_point_id: int
    code: str
    title: str
    score: float
    reason: str


class ExerciseRecommendResponse(BaseModel):
    candidates: list[ExerciseRecommendCandidate]
    provider: str
    fallback: bool
    reason: str


class ExerciseLinkRequest(BaseModel):
    knowledge_point_id: int
    confidence: float = Field(default=1.0, ge=0, le=1.0)
    reason: str = Field(default="", max_length=500)


class ExerciseAttemptCreate(BaseModel):
    knowledge_point_id: int | None = None
    result: str = Field(pattern="^(correct|wrong|unsure)$")
    note: str = Field(default="", max_length=1000)
