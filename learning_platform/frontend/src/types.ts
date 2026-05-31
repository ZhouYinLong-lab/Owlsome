export type CalculusFullImportResult = {
  ok: boolean;
  message: string;
  course_id?: number | null;
  input_path: string;
  report_path: string;
  imported: boolean;
  reset_course: boolean;
  chapters: number;
  knowledge_points: number;
  content_units: number;
  unit_counts: Record<string, number>;
};

export type KnowledgePoint = {
  id: number;
  chapter_id: number;
  code: string;
  title: string;
  summary: string;
  difficulty: number;
  tags: string;
  content_count: number;
  approved_note_count: number;
  chapter_title?: string;
  course_name?: string;
};

export type ContentUnit = {
  id: number;
  unit_type: string;
  title: string;
  content: string;
  order_index: number;
  source: string;
};

export type Note = {
  id: number;
  knowledge_point_id?: number | null;
  matched_knowledge_point_id?: number | null;
  matched_code?: string;
  matched_title?: string;
  title: string;
  content: string;
  note_type: string;
  status: string;
  match_reason: string;
  created_at: string;
};

export type KnowledgePointDetail = KnowledgePoint & {
  raw_markdown: string;
  units: ContentUnit[];
  notes: Note[];
};

export type ProgressCounts = {
  not_started: number;
  learning: number;
  mastered: number;
  difficult: number;
  total: number;
};

export type PersonalSpace = {
  id: number;
  title: string;
  source_file: string;
  source_type: string;
  status: string;
  created_at: string;
  knowledge_point_count: number;
  progress: ProgressCounts;
};

export type PersonalPoint = {
  id: number;
  space_id: number;
  code: string;
  title: string;
  summary: string;
  raw_markdown: string;
  difficulty: number;
  tags: string;
  progress_status: string;
  content_count?: number;
  units?: ContentUnit[];
};

export type PersonalSpaceDetail = PersonalSpace & {
  points: PersonalPoint[];
};

export type Contribution = {
  id: number;
  source_space_id?: number | null;
  source_personal_point_id?: number | null;
  recommended_knowledge_point_id?: number | null;
  target_knowledge_point_id?: number | null;
  contribution_type: string;
  title: string;
  content_scope: string;
  status: string;
  match_reason: string;
  duplicate_risk: string;
  created_at: string;
  recommended_code?: string;
  recommended_title?: string;
  source_space_title?: string;
  source_point_code?: string;
  source_point_title?: string;
  contributor_name?: string;
  content_preview?: string;
};

export type Stats = {
  courses: number;
  knowledge_points: number;
  content_units: number;
  pending_notes: number;
  approved_notes: number;
  qa_logs: number;
  personal_spaces: number;
  pending_contributions: number;
  approved_contributions: number;
  community_content_units: number;
  exercises: number;
  linked_exercises: number;
  exercise_attempts: number;
  mistake_attempts: number;
  unsure_attempts: number;
  weak_knowledge_points: number;
};

export type Exercise = {
  id: number;
  title: string;
  stem: string;
  answer: string;
  analysis: string;
  exercise_type: string;
  difficulty: number;
  source: string;
  status: string;
  created_at: string;
  link_confidence?: number;
  link_reason?: string;
};

export type ExerciseRecommendation = {
  knowledge_point_id: number;
  code: string;
  title: string;
  score: number;
  reason: string;
};

export type ExerciseRecommendResponse = {
  candidates: ExerciseRecommendation[];
  provider: string;
  fallback: boolean;
  reason: string;
};

export type ExerciseAttempt = {
  id: number;
  exercise_id: number;
  knowledge_point_id: number | null;
  result: string;
  note: string;
  created_at: string;
};

export type MistakeExercise = {
  attempt_id: number;
  exercise_id: number;
  knowledge_point_id: number | null;
  result: string;
  note: string;
  attempted_at: string;
  exercise_title: string;
  exercise_stem: string;
  exercise_answer: string;
  exercise_analysis: string;
  knowledge_point_code: string | null;
  knowledge_point_title: string | null;
};

export type WeakKnowledgePoint = {
  knowledge_point_id: number;
  code: string;
  title: string;
  wrong_count: number;
  unsure_count: number;
  total_weak_attempts: number;
  latest_attempt_at: string;
};

export type Tab = "dashboard" | "knowledge" | "personal" | "pipeline" | "review" | "system" | "exercises";
export type Role = "learner" | "admin";
