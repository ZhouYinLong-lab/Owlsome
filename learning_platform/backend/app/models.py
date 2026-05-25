from __future__ import annotations

from pydantic import BaseModel, Field


class ImportResult(BaseModel):
    ok: bool
    message: str
    course_id: int | None = None
    chapter_id: int | None = None
    knowledge_points: int = 0
    content_units: int = 0


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
