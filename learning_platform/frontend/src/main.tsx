import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import rehypeKatex from "rehype-katex";
import {
  BookOpen,
  Check,
  Database,
  FileText,
  FlaskConical,
  HelpCircle,
  Layers,
  Loader2,
  MessageSquare,
  Play,
  RefreshCw,
  Send,
  Upload,
  X
} from "lucide-react";
import "katex/dist/katex.min.css";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE ?? `${window.location.protocol}//${window.location.hostname}:8000`;

type Stats = {
  courses: number;
  knowledge_points: number;
  content_units: number;
  pending_notes: number;
  approved_notes: number;
  qa_logs: number;
  personal_spaces: number;
};

type KnowledgePoint = {
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
};

type ContentUnit = {
  id: number;
  unit_type: string;
  title: string;
  content: string;
  order_index: number;
  source: string;
};

type Note = {
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

type KnowledgePointDetail = KnowledgePoint & {
  raw_markdown: string;
  units: ContentUnit[];
  notes: Note[];
};

type PersonalSpace = {
  id: number;
  title: string;
  source_file: string;
  source_type: string;
  status: string;
  created_at: string;
  knowledge_point_count: number;
  progress: ProgressCounts;
};

type ProgressCounts = {
  not_started: number;
  learning: number;
  mastered: number;
  difficult: number;
  total: number;
};

type PersonalPoint = {
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

type PersonalSpaceDetail = PersonalSpace & {
  points: PersonalPoint[];
};

type Tab = "dashboard" | "knowledge" | "personal" | "review" | "pipeline";

type ObsidianBlock =
  | { type: "markdown"; content: string }
  | { type: "callout"; kind: string; title: string; content: string; folded: boolean };

const katexOptions = {
  throwOnError: false,
  strict: false
};

const sanitizeSchema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), "mark"]
};

const calloutLabels: Record<string, string> = {
  abstract: "摘要",
  bug: "问题",
  danger: "危险",
  error: "错误",
  example: "示例",
  failure: "失败",
  faq: "问答",
  help: "帮助",
  hint: "提示",
  important: "重点",
  info: "信息",
  note: "笔记",
  question: "问题",
  quote: "引用",
  success: "成功",
  summary: "摘要",
  tip: "提示",
  todo: "待办",
  warning: "警告"
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

function MarkdownSource({ children, inline = false }: { children: string; inline?: boolean }) {
  const rendered = preprocessObsidianInlineSyntax(children);
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema], [rehypeKatex, katexOptions]]}
      components={inline ? { p: React.Fragment } : undefined}
    >
      {rendered}
    </ReactMarkdown>
  );
}

function Markdown({ children }: { children: string }) {
  const blocks = parseObsidianBlocks(children);
  return (
    <div className="markdown-body">
      {blocks.map((block, index) => {
        if (block.type === "callout") {
          return (
            <div className={`obsidian-callout obsidian-callout-${block.kind}`} key={`${block.kind}-${index}`}>
              <div className="obsidian-callout-title">
                <span>{calloutLabels[block.kind] ?? block.kind}</span>
                <strong>{block.title}</strong>
              </div>
              {block.content && <MarkdownSource>{block.content}</MarkdownSource>}
            </div>
          );
        }
        return <MarkdownSource key={`markdown-${index}`}>{block.content}</MarkdownSource>;
      })}
    </div>
  );
}

function InlineMarkdown({ children }: { children: string }) {
  return (
    <span className="markdown-inline">
      <MarkdownSource inline>{children}</MarkdownSource>
    </span>
  );
}

function preprocessObsidianInlineSyntax(markdown: string) {
  return markdown
    .replace(/^---\n[\s\S]*?\n---\n?/, "")
    .replace(/!\[\[([^\]]+)\]\]/g, (_match, target) => `![${target}](${target})`)
    .replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, (_match, target, label) => `[${label}](#wikilink-${encodeURIComponent(target)})`)
    .replace(/\[\[([^\]]+)\]\]/g, (_match, target) => `[${target}](#wikilink-${encodeURIComponent(target)})`)
    .replace(/==(.+?)==/g, "<mark>$1</mark>");
}

function stripFrontmatter(markdown: string) {
  return markdown.replace(/^---\n[\s\S]*?\n---\n?/, "");
}

function parseObsidianBlocks(markdown: string): ObsidianBlock[] {
  const lines = stripFrontmatter(markdown).split(/\r?\n/);
  const blocks: ObsidianBlock[] = [];
  let buffer: string[] = [];

  function flushMarkdown() {
    const content = buffer.join("\n").trim();
    if (content) blocks.push({ type: "markdown", content });
    buffer = [];
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const match = line.match(/^>\s*\[!([a-zA-Z-]+)\]([+-])?\s*(.*)$/);

    if (!match) {
      buffer.push(line);
      continue;
    }

    flushMarkdown();
    const kind = match[1].toLowerCase();
    const folded = match[2] === "-";
    const title = (match[3] || calloutLabels[kind] || kind).trim();
    const body: string[] = [];

    // Obsidian callouts are blockquotes whose first line is > [!type].
    // Collect only the contiguous quoted lines so normal blockquotes still render normally.
    while (index + 1 < lines.length && /^>\s?/.test(lines[index + 1])) {
      index += 1;
      body.push(lines[index].replace(/^>\s?/, ""));
    }

    blocks.push({ type: "callout", kind, title, content: body.join("\n").trim(), folded });
  }

  flushMarkdown();
  return blocks;
}

function unitLabel(type: string) {
  const labels: Record<string, string> = {
    explanation: "讲解",
    definition: "定义",
    theorem: "定理",
    example: "例题",
    exercise: "习题"
  };
  return labels[type] ?? type;
}

function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [stats, setStats] = useState<Stats | null>(null);
  const [points, setPoints] = useState<KnowledgePoint[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<KnowledgePointDetail | null>(null);
  const [personalSpaces, setPersonalSpaces] = useState<PersonalSpace[]>([]);
  const [selectedSpaceId, setSelectedSpaceId] = useState<number | null>(null);
  const [personalSpace, setPersonalSpace] = useState<PersonalSpaceDetail | null>(null);
  const [selectedPersonalPointId, setSelectedPersonalPointId] = useState<number | null>(null);
  const [personalPoint, setPersonalPoint] = useState<PersonalPoint | null>(null);
  const [pending, setPending] = useState<Note[]>([]);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [filter, setFilter] = useState("全部");

  async function refreshAll(nextSelectedId?: number | null) {
    const [nextStats, nextPoints, nextPending, nextSpaces] = await Promise.all([
      api<Stats>("/api/stats"),
      api<KnowledgePoint[]>("/api/knowledge-points"),
      api<Note[]>("/api/notes/pending"),
      api<PersonalSpace[]>("/api/personal-spaces")
    ]);
    setStats(nextStats);
    setPoints(nextPoints);
    setPending(nextPending);
    setPersonalSpaces(nextSpaces);
    const targetId = nextSelectedId ?? selectedId ?? nextPoints[0]?.id ?? null;
    setSelectedId(targetId);
    if (targetId) {
      setDetail(await api<KnowledgePointDetail>(`/api/knowledge-points/${targetId}`));
    } else {
      setDetail(null);
    }
  }

  async function loadPersonalSpace(spaceId: number, pointId?: number | null) {
    const space = await api<PersonalSpaceDetail>(`/api/personal-spaces/${spaceId}`);
    setSelectedSpaceId(spaceId);
    setPersonalSpace(space);
    const targetPointId = pointId ?? selectedPersonalPointId ?? space.points[0]?.id ?? null;
    setSelectedPersonalPointId(targetPointId);
    setPersonalPoint(
      targetPointId
        ? await api<PersonalPoint>(`/api/personal-spaces/${spaceId}/knowledge-points/${targetPointId}`)
        : null
    );
  }

  async function refreshPersonal(spaceId?: number | null, pointId?: number | null) {
    const spaces = await api<PersonalSpace[]>("/api/personal-spaces");
    setPersonalSpaces(spaces);
    const targetSpaceId = spaceId ?? selectedSpaceId ?? spaces[0]?.id ?? null;
    if (targetSpaceId) {
      await loadPersonalSpace(targetSpaceId, pointId);
    }
  }

  async function createPersonalFromSample() {
    setBusy("personal-sample");
    try {
      const result = await api<{ space_id: number; message: string }>("/api/personal-spaces/from-sample", { method: "POST" });
      setMessage(result.message);
      await refreshPersonal(result.space_id, null);
      setTab("personal");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "创建个人空间失败");
    } finally {
      setBusy("");
    }
  }

  async function uploadMarkdown(file: File) {
    setBusy("personal-upload");
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch(`${API_BASE}/api/personal-spaces/upload-markdown`, { method: "POST", body });
      if (!res.ok) throw new Error(await res.text());
      const result = await res.json() as { space_id: number; message: string };
      setMessage(result.message);
      await refreshPersonal(result.space_id, null);
      setTab("personal");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "上传失败");
    } finally {
      setBusy("");
    }
  }

  useEffect(() => {
    refreshAll().catch((err) => setMessage(`后端连接失败：${err.message}`));
  }, []);

  async function importSample() {
    setBusy("import");
    try {
      const result = await api<{ message: string }>("/api/import/sample", { method: "POST" });
      setMessage(result.message);
      await refreshAll();
      setTab("knowledge");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "导入失败");
    } finally {
      setBusy("");
    }
  }

  async function selectPoint(id: number) {
    setSelectedId(id);
    setDetail(await api<KnowledgePointDetail>(`/api/knowledge-points/${id}`));
  }

  async function approveNote(noteId: number) {
    setBusy(`approve-${noteId}`);
    await api(`/api/notes/${noteId}/approve`, { method: "POST" });
    await refreshAll(selectedId);
    setBusy("");
  }

  async function rejectNote(noteId: number) {
    setBusy(`reject-${noteId}`);
    await api(`/api/notes/${noteId}/reject`, { method: "POST" });
    await refreshAll(selectedId);
    setBusy("");
  }

  const filteredPoints = useMemo(() => {
    if (filter === "全部") return points;
    return points.filter((point) => point.tags.includes(filter) || point.title.includes(filter));
  }, [filter, points]);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark"><BookOpen size={24} /></div>
          <div>
            <strong>AI 数学学习平台</strong>
            <span>EL 交互组 Demo</span>
          </div>
        </div>
        <nav>
          <button className={tab === "dashboard" ? "active" : ""} onClick={() => setTab("dashboard")} title="控制台">
            <Database size={18} /> 控制台
          </button>
          <button className={tab === "knowledge" ? "active" : ""} onClick={() => setTab("knowledge")} title="公共知识库">
            <Layers size={18} /> 公共知识库
          </button>
          <button className={tab === "personal" ? "active" : ""} onClick={() => setTab("personal")} title="个人学习空间">
            <Upload size={18} /> 个人学习空间
          </button>
          <button className={tab === "review" ? "active" : ""} onClick={() => setTab("review")} title="笔记审核">
            <Check size={18} /> 笔记审核
          </button>
          <button className={tab === "pipeline" ? "active" : ""} onClick={() => setTab("pipeline")} title="资料处理">
            <FlaskConical size={18} /> 资料处理
          </button>
        </nav>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">公共教材知识库构建 + 笔记审核合并</p>
            <h1>把静态微积分教材变成可审核、可问答的学习单元</h1>
          </div>
          <button className="primary" onClick={importSample} disabled={busy === "import"} title="一键导入样例">
            {busy === "import" ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
            一键导入样例
          </button>
        </header>

        {message && <div className="notice">{message}</div>}

        {tab === "dashboard" && (
          <Dashboard stats={stats} onImport={importSample} busy={busy === "import"} />
        )}
        {tab === "knowledge" && (
          <KnowledgeBase
            points={filteredPoints}
            selectedId={selectedId}
            detail={detail}
            filter={filter}
            onFilter={setFilter}
            onSelect={selectPoint}
            onRefresh={() => refreshAll(selectedId)}
          />
        )}
        {tab === "personal" && (
          <PersonalSpaces
            spaces={personalSpaces}
            selectedSpaceId={selectedSpaceId}
            space={personalSpace}
            selectedPointId={selectedPersonalPointId}
            point={personalPoint}
            busy={busy}
            onCreateSample={createPersonalFromSample}
            onUpload={uploadMarkdown}
            onSelectSpace={(spaceId) => loadPersonalSpace(spaceId, null)}
            onSelectPoint={(spaceId, pointId) => loadPersonalSpace(spaceId, pointId)}
            onRefresh={() => refreshPersonal(selectedSpaceId, selectedPersonalPointId)}
          />
        )}
        {tab === "review" && (
          <Review notes={pending} busy={busy} onApprove={approveNote} onReject={rejectNote} />
        )}
        {tab === "pipeline" && <Pipeline />}
      </main>
    </div>
  );
}

function Dashboard({ stats, onImport, busy }: { stats: Stats | null; onImport: () => void; busy: boolean }) {
  const cards = [
    ["课程", stats?.courses ?? 0, BookOpen],
    ["知识点", stats?.knowledge_points ?? 0, Layers],
    ["内容单元", stats?.content_units ?? 0, FileText],
    ["待审核笔记", stats?.pending_notes ?? 0, Check],
    ["已合并笔记", stats?.approved_notes ?? 0, Upload],
    ["个人空间", stats?.personal_spaces ?? 0, Database],
    ["问答记录", stats?.qa_logs ?? 0, MessageSquare]
  ] as const;
  return (
    <section className="dashboard">
      <div className="statsGrid">
        {cards.map(([label, value, Icon]) => (
          <div className="metric" key={label}>
            <Icon size={20} />
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <div className="flow">
        <h2>演示闭环</h2>
        <div className="flowSteps">
          {["MinerU Markdown", "规则切分", "知识库展示", "笔记审核", "知识点问答"].map((step, index) => (
            <div className="step" key={step}>
              <span>{index + 1}</span>
              <strong>{step}</strong>
            </div>
          ))}
        </div>
        <button className="primary" onClick={onImport} disabled={busy} title="导入样例知识库">
          {busy ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
          从已有解析结果导入第 5 章 5.1-5.2
        </button>
      </div>
    </section>
  );
}

function KnowledgeBase(props: {
  points: KnowledgePoint[];
  selectedId: number | null;
  detail: KnowledgePointDetail | null;
  filter: string;
  onFilter: (value: string) => void;
  onSelect: (id: number) => void;
  onRefresh: () => void;
}) {
  return (
    <section className="workspace">
      <div className="listPane">
        <div className="paneHead">
          <h2>知识点目录</h2>
          <button className="iconButton" onClick={props.onRefresh} title="刷新">
            <RefreshCw size={17} />
          </button>
        </div>
        <div className="filters">
          {["全部", "极限", "连续性", "偏导数", "全微分", "例题"].map((item) => (
            <button key={item} className={props.filter === item ? "active" : ""} onClick={() => props.onFilter(item)}>
              {item}
            </button>
          ))}
        </div>
        <div className="pointList">
          {props.points.map((point) => (
            <button
              key={point.id}
              className={props.selectedId === point.id ? "point selected" : "point"}
              onClick={() => props.onSelect(point.id)}
            >
              <span>{point.code}</span>
              <strong><InlineMarkdown>{point.title}</InlineMarkdown></strong>
              <small>{point.content_count} 个内容单元 · {point.approved_note_count} 条笔记</small>
            </button>
          ))}
        </div>
      </div>
      <DetailPane detail={props.detail} />
    </section>
  );
}

function DetailPane({ detail }: { detail: KnowledgePointDetail | null }) {
  const [question, setQuestion] = useState("这个知识点考试时最容易错在哪里？");
  const [answer, setAnswer] = useState("");
  const [noteTitle, setNoteTitle] = useState("课堂补充");
  const [noteContent, setNoteContent] = useState("二重极限要检查不同路径趋近时的结果是否一致，不能只看一条直线。");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    setAnswer("");
  }, [detail?.id]);

  if (!detail) {
    return <div className="detailPane empty">请先导入样例并选择一个知识点。</div>;
  }

  async function submitNote() {
    setBusy("note");
    await api("/api/notes", {
      method: "POST",
      body: JSON.stringify({
        title: noteTitle,
        content: noteContent,
        knowledge_point_id: detail?.id,
        note_type: "student_note"
      })
    });
    setBusy("");
    setNoteContent("");
  }

  async function ask() {
    setBusy("qa");
    const res = await api<{ answer: string; mode: string }>("/api/qa", {
      method: "POST",
      body: JSON.stringify({ knowledge_point_id: detail?.id, question })
    });
    setAnswer(`${res.answer}\n\n回答模式：${res.mode}`);
    setBusy("");
  }

  return (
    <div className="detailPane">
      <div className="detailHeader">
        <span>{detail.code}</span>
        <h2><InlineMarkdown>{detail.title}</InlineMarkdown></h2>
        <p>{detail.summary}</p>
      </div>

      <div className="unitStack">
        {detail.units.map((unit) => (
          <article className={`unit ${unit.unit_type}`} key={unit.id}>
            <div className="unitHead">
              <span>{unitLabel(unit.unit_type)}</span>
              <strong><InlineMarkdown>{unit.title || "教材内容"}</InlineMarkdown></strong>
            </div>
            <Markdown>{unit.content}</Markdown>
          </article>
        ))}
      </div>

      <section className="interactionGrid">
        <div className="toolPanel">
          <h3><Upload size={18} /> 上传课堂笔记</h3>
          <input value={noteTitle} onChange={(event) => setNoteTitle(event.target.value)} aria-label="笔记标题" />
          <textarea value={noteContent} onChange={(event) => setNoteContent(event.target.value)} aria-label="笔记内容" />
          <button className="primary" onClick={submitNote} disabled={busy === "note"} title="提交到审核区">
            {busy === "note" ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
            提交审核
          </button>
        </div>

        <div className="toolPanel">
          <h3><HelpCircle size={18} /> 当前知识点问答</h3>
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="问题" />
          <button className="primary" onClick={ask} disabled={busy === "qa"} title="基于当前知识点提问">
            {busy === "qa" ? <Loader2 className="spin" size={18} /> : <MessageSquare size={18} />}
            提问
          </button>
          {answer && <div className="answer"><Markdown>{answer}</Markdown></div>}
        </div>
      </section>

      <section className="approvedNotes">
        <h3>已合并笔记</h3>
        {detail.notes.length === 0 ? <p>暂无已审核笔记。</p> : detail.notes.map((note) => (
          <div className="note" key={note.id}>
            <strong>{note.title || "学生笔记"}</strong>
            <p>{note.content}</p>
          </div>
        ))}
      </section>
    </div>
  );
}

function progressLabel(status: string) {
  const labels: Record<string, string> = {
    not_started: "未开始",
    learning: "学习中",
    mastered: "已掌握",
    difficult: "疑难点"
  };
  return labels[status] ?? status;
}

function PersonalSpaces(props: {
  spaces: PersonalSpace[];
  selectedSpaceId: number | null;
  space: PersonalSpaceDetail | null;
  selectedPointId: number | null;
  point: PersonalPoint | null;
  busy: string;
  onCreateSample: () => void;
  onUpload: (file: File) => void;
  onSelectSpace: (spaceId: number) => void;
  onSelectPoint: (spaceId: number, pointId: number) => void;
  onRefresh: () => void;
}) {
  return (
    <section className="personalLayout">
      <div className="personalLeft">
        <UploadMarkdownPanel
          busy={props.busy}
          onCreateSample={props.onCreateSample}
          onUpload={props.onUpload}
        />
        <div className="listPane">
          <div className="paneHead">
            <h2>个人空间</h2>
            <button className="iconButton" onClick={props.onRefresh} title="刷新个人空间">
              <RefreshCw size={17} />
            </button>
          </div>
          <div className="pointList">
            {props.spaces.map((space) => (
              <button
                key={space.id}
                className={props.selectedSpaceId === space.id ? "point selected" : "point"}
                onClick={() => props.onSelectSpace(space.id)}
              >
                <span>{space.source_type}</span>
                <strong><InlineMarkdown>{space.title}</InlineMarkdown></strong>
                <small>
                  {space.knowledge_point_count} 个知识点 · 已掌握 {space.progress.mastered}/{space.progress.total}
                </small>
              </button>
            ))}
            {props.spaces.length === 0 && <div className="emptyState">还没有个人空间，先上传 Markdown 或使用样例。</div>}
          </div>
        </div>
      </div>
      <PersonalSpaceDetailView
        space={props.space}
        point={props.point}
        selectedPointId={props.selectedPointId}
        busy={props.busy}
        onSelectPoint={props.onSelectPoint}
        onRefresh={props.onRefresh}
      />
    </section>
  );
}

function UploadMarkdownPanel({ busy, onCreateSample, onUpload }: {
  busy: string;
  onCreateSample: () => void;
  onUpload: (file: File) => void;
}) {
  return (
    <div className="uploadPanel">
      <h2>上传个人资料</h2>
      <label className="filePicker">
        <Upload size={18} />
        <span>{busy === "personal-upload" ? "正在生成空间..." : "选择 Markdown / TXT"}</span>
        <input
          type="file"
          accept=".md,.markdown,.txt"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onUpload(file);
            event.currentTarget.value = "";
          }}
        />
      </label>
      <button className="primary" onClick={onCreateSample} disabled={busy === "personal-sample"} title="用已有 MinerU 样例创建个人空间">
        {busy === "personal-sample" ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
        用样例创建个人空间
      </button>
      <button className="disabledAction" disabled title="PDF 解析占位">
        <FileText size={18} />
        PDF 上传接入 MinerU 解析中
      </button>
      <p>第一版真实支持 Markdown 上传；PDF 后续会走 mineru_tools → text_archiver → 个人空间链路。</p>
    </div>
  );
}

function PersonalSpaceDetailView(props: {
  space: PersonalSpaceDetail | null;
  point: PersonalPoint | null;
  selectedPointId: number | null;
  busy: string;
  onSelectPoint: (spaceId: number, pointId: number) => void;
  onRefresh: () => void;
}) {
  if (!props.space) {
    return <div className="detailPane empty">选择或创建一个个人学习空间。</div>;
  }
  return (
    <div className="personalDetail">
      <div className="spaceHeader">
        <div>
          <span>{props.space.source_type}</span>
          <h2>{props.space.title}</h2>
          <p>{props.space.source_file}</p>
        </div>
        <ProgressSummary progress={props.space.progress} />
      </div>
      <div className="personalWorkspace">
        <div className="listPane compact">
          <h3>个人目录</h3>
          <div className="pointList">
            {props.space.points.map((point) => (
              <button
                key={point.id}
                className={props.selectedPointId === point.id ? "point selected" : "point"}
                onClick={() => props.onSelectPoint(props.space!.id, point.id)}
              >
                <span>{point.code}</span>
                <strong><InlineMarkdown>{point.title}</InlineMarkdown></strong>
                <small>{progressLabel(point.progress_status)} · {point.content_count ?? 0} 个内容单元</small>
              </button>
            ))}
          </div>
        </div>
        <PersonalPointDetail spaceId={props.space.id} point={props.point} onRefresh={props.onRefresh} />
      </div>
    </div>
  );
}

function ProgressSummary({ progress }: { progress: ProgressCounts }) {
  const total = progress.total || 1;
  return (
    <div className="progressBox">
      <strong>{Math.round((progress.mastered / total) * 100)}%</strong>
      <span>已掌握</span>
      <div className="progressBar">
        <i style={{ width: `${(progress.mastered / total) * 100}%` }} />
      </div>
      <small>学习中 {progress.learning} · 疑难 {progress.difficult} · 未开始 {progress.not_started}</small>
    </div>
  );
}

function PersonalPointDetail({ spaceId, point, onRefresh }: {
  spaceId: number;
  point: PersonalPoint | null;
  onRefresh: () => void;
}) {
  const [question, setQuestion] = useState("请基于我上传的资料总结这个知识点。");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState("");
  const [hint, setHint] = useState("");

  useEffect(() => {
    setAnswer("");
    setHint("");
  }, [point?.id]);

  if (!point) {
    return <div className="detailPane empty">请选择一个个人知识点。</div>;
  }

  async function setProgress(status: string) {
    setBusy(status);
    await api(`/api/personal-spaces/${spaceId}/knowledge-points/${point?.id}/progress`, {
      method: "POST",
      body: JSON.stringify({ status })
    });
    await onRefresh();
    setBusy("");
  }

  async function ask() {
    setBusy("personal-qa");
    const res = await api<{ answer: string; mode: string }>(`/api/personal-spaces/${spaceId}/qa`, {
      method: "POST",
      body: JSON.stringify({ personal_knowledge_point_id: point?.id, question })
    });
    setAnswer(`${res.answer}\n\n回答模式：${res.mode}`);
    setBusy("");
  }

  return (
    <div className="detailPane">
      <div className="detailHeader">
        <span>{point.code} · {progressLabel(point.progress_status)}</span>
        <h2><InlineMarkdown>{point.title}</InlineMarkdown></h2>
        <p>{point.summary}</p>
      </div>

      <div className="progressActions">
        {["not_started", "learning", "mastered", "difficult"].map((status) => (
          <button
            key={status}
            className={point.progress_status === status ? "active" : ""}
            disabled={busy === status}
            onClick={() => setProgress(status)}
          >
            {progressLabel(status)}
          </button>
        ))}
        <button className="ghostButton" onClick={() => setHint("第一版只做申请入口展示；后续会进入公共库审核队列。")}>
          申请贡献到公共库
        </button>
      </div>
      {hint && <div className="notice">{hint}</div>}

      <div className="unitStack">
        {(point.units ?? []).map((unit) => (
          <article className={`unit ${unit.unit_type}`} key={unit.id}>
            <div className="unitHead">
              <span>{unitLabel(unit.unit_type)}</span>
              <strong><InlineMarkdown>{unit.title || "个人资料内容"}</InlineMarkdown></strong>
            </div>
            <Markdown>{unit.content}</Markdown>
          </article>
        ))}
      </div>

      <div className="toolPanel personalQa">
        <h3><MessageSquare size={18} /> 当前个人资料问答</h3>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="个人空间问题" />
        <button className="primary" onClick={ask} disabled={busy === "personal-qa"}>
          {busy === "personal-qa" ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
          提问
        </button>
        {answer && <div className="answer"><Markdown>{answer}</Markdown></div>}
      </div>
    </div>
  );
}

function Review({ notes, busy, onApprove, onReject }: {
  notes: Note[];
  busy: string;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
}) {
  return (
    <section className="review">
      <h2>待审核笔记</h2>
      {notes.length === 0 ? <div className="emptyState">暂无待审核笔记。</div> : notes.map((note) => (
        <article className="reviewItem" key={note.id}>
          <div>
            <span className="status">pending</span>
            <h3>{note.title || "学生笔记"}</h3>
            <p>{note.content}</p>
            <small>{note.match_reason}</small>
          </div>
          <div className="reviewActions">
            <button className="primary" onClick={() => onApprove(note.id)} disabled={busy === `approve-${note.id}`} title="审核通过">
              <Check size={17} /> 通过
            </button>
            <button className="danger" onClick={() => onReject(note.id)} disabled={busy === `reject-${note.id}`} title="驳回">
              <X size={17} /> 驳回
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}

function Pipeline() {
  return (
    <section className="pipeline">
      <h2>资料处理链路</h2>
      <div className="pipelineGrid">
        <div>
          <FileText size={24} />
          <strong>mineru_tools</strong>
          <p>复用现有 PDF → Markdown 能力。公共库和个人样例都可读取已经生成的 `merged_full.md`，避免现场解析耗时。</p>
        </div>
        <div>
          <FlaskConical size={24} />
          <strong>text_archiver</strong>
          <p>复用 Markdown 清洗思路。配置 OpenRouter Key 后，可把清洗作为导入前的可选步骤。</p>
        </div>
        <div>
          <Layers size={24} />
          <strong>learning_platform</strong>
          <p>新增规则切分、SQLite 存储、公共知识库、个人学习空间、进度标记与问答展示。</p>
        </div>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
