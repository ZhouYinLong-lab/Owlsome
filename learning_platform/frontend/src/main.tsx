import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import rehypeKatex from "rehype-katex";
import {
  BarChart3,
  BookOpen,
  Check,
  Database,
  FileText,
  FlaskConical,
  FolderTree,
  HelpCircle,
  Home,
  Layers,
  Loader2,
  MessageSquare,
  Play,
  RefreshCw,
  Send,
  ShieldCheck,
  Upload,
  UserRound,
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
  pending_contributions: number;
  approved_contributions: number;
  community_content_units: number;
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

type Contribution = {
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

type Tab = "dashboard" | "knowledge" | "personal" | "pipeline" | "review" | "system";
type Role = "learner" | "admin";

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

function sourceLabel(source?: string) {
  if (!source) return "";
  if (source.startsWith("community_contribution:")) return "社区贡献";
  if (source.includes("text_archiver")) return "清洗版教材";
  if (source.includes("MinerU")) return "MinerU 原文";
  return source;
}

function pageMeta(tab: Tab, role: Role) {
  const adminSuffix = role === "admin" ? " · 管理员模式" : "";
  const meta: Record<Tab, { eyebrow: string; title: string }> = {
    dashboard: {
      eyebrow: `Owlsome Learning${adminSuffix}`,
      title: "今天从哪里开始学习？"
    },
    knowledge: {
      eyebrow: "公共资源库",
      title: "按学科、教材和章节浏览公共知识"
    },
    personal: {
      eyebrow: "个人学习空间",
      title: "把自己的资料整理成可问答的学习路径"
    },
    pipeline: {
      eyebrow: "资料处理链路",
      title: "从 PDF 到 Obsidian Markdown，再到知识库"
    },
    review: {
      eyebrow: "管理员工作台",
      title: "审核贡献与笔记，决定哪些内容进入公共库"
    },
    system: {
      eyebrow: "系统概览",
      title: "查看演示数据、导入状态和运行指标"
    }
  };
  return meta[tab];
}

function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [role, setRole] = useState<Role>("learner");
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
  const [pendingContributions, setPendingContributions] = useState<Contribution[]>([]);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  async function refreshAll(nextSelectedId?: number | null) {
    const [nextStats, nextPoints, nextPending, nextContributions, nextSpaces] = await Promise.all([
      api<Stats>("/api/stats"),
      api<KnowledgePoint[]>("/api/knowledge-points"),
      api<Note[]>("/api/notes/pending"),
      api<Contribution[]>("/api/contributions/pending"),
      api<PersonalSpace[]>("/api/personal-spaces")
    ]);
    setStats(nextStats);
    setPoints(nextPoints);
    setPending(nextPending);
    setPendingContributions(nextContributions);
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

  useEffect(() => {
    if (role === "learner" && (tab === "review" || tab === "system")) {
      setTab("dashboard");
    }
  }, [role, tab]);

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

  async function reviewContribution(contributionId: number, action: "approve" | "reject" | "request-revision") {
    setBusy(`${action}-contribution-${contributionId}`);
    await api(`/api/contributions/${contributionId}/${action}`, {
      method: "POST",
      body: JSON.stringify({ comment: action === "approve" ? "审核通过，合并到公共知识库。" : "" })
    });
    await refreshAll(selectedId);
    setBusy("");
  }

  const meta = pageMeta(tab, role);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark"><BookOpen size={24} /></div>
          <div>
            <strong>Owlsome Learning</strong>
            <span>猫头鹰组 · EL Demo</span>
          </div>
        </div>
        <nav>
          <button className={tab === "dashboard" ? "active" : ""} onClick={() => setTab("dashboard")} title="控制台">
            <Home size={18} /> 工作台
          </button>
          <button className={tab === "knowledge" ? "active" : ""} onClick={() => setTab("knowledge")} title="公共知识库">
            <FolderTree size={18} /> 公共资源库
          </button>
          <button className={tab === "personal" ? "active" : ""} onClick={() => setTab("personal")} title="个人学习空间">
            <UserRound size={18} /> 个人学习空间
          </button>
          <button className={tab === "pipeline" ? "active" : ""} onClick={() => setTab("pipeline")} title="资料处理">
            <FlaskConical size={18} /> 资料处理
          </button>
          {role === "admin" && (
            <>
              <div className="navDivider">管理员</div>
              <button className={tab === "review" ? "active" : ""} onClick={() => setTab("review")} title="审核中心">
                <ShieldCheck size={18} /> 审核中心
              </button>
              <button className={tab === "system" ? "active" : ""} onClick={() => setTab("system")} title="系统概览">
                <BarChart3 size={18} /> 系统概览
              </button>
            </>
          )}
        </nav>
        <div className="roleSwitch" aria-label="本地演示角色切换">
          <span>{role === "admin" ? "管理员模式" : "学习者模式"}</span>
          <button onClick={() => setRole(role === "admin" ? "learner" : "admin")}>
            {role === "admin" ? <UserRound size={16} /> : <ShieldCheck size={16} />}
            切换为{role === "admin" ? "学习者" : "管理员"}
          </button>
          <small>本地演示隔离；正式权限后续接入南哪小帮手。</small>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div>
            <p className="eyebrow">{meta.eyebrow}</p>
            <h1>{meta.title}</h1>
          </div>
          {role === "admin" && (
            <button className="primary" onClick={importSample} disabled={busy === "import"} title="一键导入样例">
              {busy === "import" ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              一键导入样例
            </button>
          )}
        </header>

        {message && <div className="notice">{message}</div>}

        {tab === "dashboard" && (
          <Dashboard
            stats={stats}
            spaces={personalSpaces}
            points={points}
            onNavigate={setTab}
          />
        )}
        {tab === "knowledge" && (
          <KnowledgeBase
            points={points}
            selectedId={selectedId}
            detail={detail}
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
            onContributionCreated={() => refreshAll(selectedId)}
          />
        )}
        {tab === "review" && (
          <Review
            notes={pending}
            contributions={pendingContributions}
            busy={busy}
            onApprove={approveNote}
            onReject={rejectNote}
            onContributionAction={reviewContribution}
          />
        )}
        {tab === "system" && role === "admin" && (
          <SystemOverview stats={stats} onImport={importSample} busy={busy === "import"} />
        )}
        {tab === "pipeline" && <Pipeline />}
      </main>
    </div>
  );
}

function Dashboard({ stats, spaces, points, onNavigate }: {
  stats: Stats | null;
  spaces: PersonalSpace[];
  points: KnowledgePoint[];
  onNavigate: (tab: Tab) => void;
}) {
  const recentSpace = spaces[0];
  const progress = recentSpace?.progress;
  const mastered = progress ? `${progress.mastered}/${progress.total}` : "0/0";
  const cards = [
    ["公共资源", stats?.knowledge_points ?? 0, FolderTree],
    ["个人空间", stats?.personal_spaces ?? 0, UserRound],
    ["学习进度", mastered, Check],
    ["贡献状态", `${stats?.pending_contributions ?? 0} 待审 / ${stats?.approved_contributions ?? 0} 已合并`, ShieldCheck]
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

      <div className="workbenchGrid">
        <article className="workbenchCard">
          <span><UserRound size={18} /> 继续学习</span>
          <h2>{recentSpace?.title ?? "还没有个人学习空间"}</h2>
          <p>
            {recentSpace
              ? `已掌握 ${mastered} 个知识点，疑难 ${recentSpace.progress.difficult} 个。`
              : "上传 Markdown 或使用样例资料后，这里会显示最近学习进度。"}
          </p>
          <button className="primary" onClick={() => onNavigate("personal")}>
            进入个人学习空间
          </button>
        </article>

        <article className="workbenchCard">
          <span><FolderTree size={18} /> 公共资源</span>
          <h2>数学 / 微积分 II（第四版）</h2>
          <p>当前公共库包含 {points.length} 个知识点，已按教材章节组织，适合作为团队共建底座。</p>
          <button className="primary" onClick={() => onNavigate("knowledge")}>
            浏览公共资源库
          </button>
        </article>

        <article className="workbenchCard">
          <span><ShieldCheck size={18} /> 贡献状态</span>
          <h2>{stats?.approved_contributions ?? 0} 条已合并贡献</h2>
          <p>个人资料默认保持私有；主动提交并通过审核后，才会进入公共知识库。</p>
          <button className="ghostButton" onClick={() => onNavigate("personal")}>
            从个人空间发起贡献
          </button>
        </article>
      </div>

      <div className="flow">
        <h2>核心闭环</h2>
        <div className="flowSteps">
          {["私人学习", "主动贡献", "管理员审核", "进入公共库", "问答复用"].map((step, index) => (
            <div className="step" key={step}>
              <span>{index + 1}</span>
              <strong>{step}</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function groupPointsByChapter(points: KnowledgePoint[]) {
  const groups = new Map<string, KnowledgePoint[]>();
  for (const point of points) {
    const chapter = point.chapter_title || "未分章资源";
    groups.set(chapter, [...(groups.get(chapter) ?? []), point]);
  }
  return [...groups.entries()].map(([chapter, chapterPoints]) => ({ chapter, points: chapterPoints }));
}

function KnowledgeBase(props: {
  points: KnowledgePoint[];
  selectedId: number | null;
  detail: KnowledgePointDetail | null;
  onSelect: (id: number) => void;
  onRefresh: () => void;
}) {
  const chapters = useMemo(() => groupPointsByChapter(props.points), [props.points]);
  const communityUnits = props.detail?.units.filter((unit) => unit.source?.startsWith("community_contribution:")).length ?? 0;
  const sourceTags = props.detail
    ? Array.from(new Set(props.detail.units.map((unit) => sourceLabel(unit.source)).filter(Boolean)))
    : [];
  return (
    <section className="workspace">
      <div className="listPane">
        <div className="paneHead">
          <h2>公共资源库</h2>
          <button className="iconButton" onClick={props.onRefresh} title="刷新">
            <RefreshCw size={17} />
          </button>
        </div>
        <div className="resourceTree">
          <div className="treeNode root"><FolderTree size={16} /> 数学</div>
          <div className="treeNode course"><BookOpen size={16} /> 微积分 II（第四版）</div>
          {chapters.map((group) => (
            <div className="treeGroup" key={group.chapter}>
              <div className="treeNode chapter"><Layers size={16} /> {group.chapter}</div>
              <small>{group.points.length} 个知识点 · {sourceTags[0] ?? "教材资源"}</small>
            </div>
          ))}
        </div>
        <div className="pointList grouped">
          {chapters.map((group) => (
            <div className="chapterGroup" key={group.chapter}>
              <h3>{group.chapter}</h3>
              {group.points.map((point) => (
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
          ))}
        </div>
      </div>
      <DetailPane detail={props.detail} communityUnits={communityUnits} sourceTags={sourceTags} />
    </section>
  );
}

function DetailPane({ detail, communityUnits, sourceTags }: {
  detail: KnowledgePointDetail | null;
  communityUnits: number;
  sourceTags: string[];
}) {
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
        <div className="resourceTags">
          {sourceTags.map((tag) => <em key={tag}>{tag}</em>)}
          {communityUnits > 0 && <em>社区贡献 {communityUnits}</em>}
        </div>
      </div>

      <div className="unitStack">
        {detail.units.map((unit) => (
          <article className={`unit ${unit.unit_type}`} key={unit.id}>
            <div className="unitHead">
              <span>{unitLabel(unit.unit_type)}</span>
              <strong><InlineMarkdown>{unit.title || "教材内容"}</InlineMarkdown></strong>
              {sourceLabel(unit.source) && (
                <em className={unit.source?.startsWith("community_contribution:") ? "communityBadge" : "sourceBadge"}>
                  {sourceLabel(unit.source)}
                </em>
              )}
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
  onContributionCreated: () => void;
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
            <h2>我的资料</h2>
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
        onContributionCreated={props.onContributionCreated}
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
      <h2>创建学习空间</h2>
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
        PDF 上传接入中
      </button>
      <p>PDF 解析将接入 MinerU + text_archiver，当前演示请使用 Markdown 或样例资料。</p>
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
  onContributionCreated: () => void;
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
          <h3>资料目录</h3>
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
        <PersonalPointDetail
          spaceId={props.space.id}
          point={props.point}
          onRefresh={props.onRefresh}
          onContributionCreated={props.onContributionCreated}
        />
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

function PersonalPointDetail({ spaceId, point, onRefresh, onContributionCreated }: {
  spaceId: number;
  point: PersonalPoint | null;
  onRefresh: () => void;
  onContributionCreated: () => void;
}) {
  const [question, setQuestion] = useState("请基于我上传的资料总结这个知识点。");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState("");
  const [hint, setHint] = useState("");
  const [showContributionForm, setShowContributionForm] = useState(false);
  const [contributionTitle, setContributionTitle] = useState("");
  const [contributionType, setContributionType] = useState("note");

  useEffect(() => {
    setAnswer("");
    setHint("");
    setShowContributionForm(false);
    setContributionTitle(point?.title ?? "");
    setContributionType("note");
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

  async function submitContribution() {
    setBusy("contribution");
    const result = await api<Contribution>("/api/contributions/from-personal-point", {
      method: "POST",
      body: JSON.stringify({
        space_id: spaceId,
        personal_knowledge_point_id: point?.id,
        contribution_type: contributionType,
        title: contributionTitle || point?.title,
        content_scope: "whole_point"
      })
    });
    setHint(
      `已进入审核队列，推荐合并到 ${result.recommended_code ?? ""} ${result.recommended_title ?? "待人工确认"}。${result.match_reason}`
    );
    setShowContributionForm(false);
    await onContributionCreated();
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
        <button className="ghostButton" onClick={() => setShowContributionForm((value) => !value)}>
          申请贡献到公共库
        </button>
      </div>
      {hint && <div className="notice">{hint}</div>}
      {showContributionForm && (
        <div className="contributionForm">
          <h3>申请贡献到公共知识库</h3>
          <p>上传资料默认保留在私人空间；只有提交并审核通过后，内容才会进入公共知识库。</p>
          <input
            value={contributionTitle}
            onChange={(event) => setContributionTitle(event.target.value)}
            aria-label="贡献标题"
          />
          <select value={contributionType} onChange={(event) => setContributionType(event.target.value)} aria-label="贡献类型">
            <option value="note">笔记</option>
            <option value="explanation">讲解</option>
            <option value="example">例题</option>
            <option value="exercise">习题</option>
            <option value="mistake">易错点</option>
            <option value="faq">FAQ</option>
          </select>
          <div className="formActions">
            <button className="primary" onClick={submitContribution} disabled={busy === "contribution"}>
              {busy === "contribution" ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
              提交到审核队列
            </button>
            <button className="ghostButton" onClick={() => setShowContributionForm(false)}>取消</button>
          </div>
        </div>
      )}

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

function contributionLabel(type: string) {
  const labels: Record<string, string> = {
    note: "笔记",
    explanation: "讲解",
    example: "例题",
    exercise: "习题",
    mistake: "易错点",
    faq: "FAQ"
  };
  return labels[type] ?? type;
}

function Review({ notes, contributions, busy, onApprove, onReject, onContributionAction }: {
  notes: Note[];
  contributions: Contribution[];
  busy: string;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
  onContributionAction: (id: number, action: "approve" | "reject" | "request-revision") => void;
}) {
  return (
    <section className="review">
      <h2>审核中心</h2>
      <div className="reviewGroup">
        <h3>待审核贡献</h3>
        {contributions.length === 0 ? <div className="emptyState">暂无待审核贡献。</div> : contributions.map((contribution) => (
          <article className="reviewItem contributionReview" key={contribution.id}>
            <div>
              <span className="status">pending · {contributionLabel(contribution.contribution_type)}</span>
              <h3>{contribution.title || "社区贡献"}</h3>
              <div className="previewBox">
                <Markdown>{contribution.content_preview || "暂无内容预览"}</Markdown>
              </div>
              <small>
                来源：{contribution.source_space_title || "个人空间"} / {contribution.source_point_code || ""} {contribution.source_point_title || "个人知识点"}
              </small>
              <small>
                推荐：{contribution.recommended_code || ""} {contribution.recommended_title || "待人工确认"} · {contribution.match_reason}
              </small>
              <small>{contribution.duplicate_risk}</small>
            </div>
            <div className="reviewActions">
              <button
                className="primary"
                onClick={() => onContributionAction(contribution.id, "approve")}
                disabled={busy === `approve-contribution-${contribution.id}`}
                title="贡献审核通过"
              >
                <Check size={17} /> 通过
              </button>
              <button
                className="ghostButton"
                onClick={() => onContributionAction(contribution.id, "request-revision")}
                disabled={busy === `request-revision-contribution-${contribution.id}`}
                title="要求贡献者修改"
              >
                <RefreshCw size={17} /> 修改
              </button>
              <button
                className="danger"
                onClick={() => onContributionAction(contribution.id, "reject")}
                disabled={busy === `reject-contribution-${contribution.id}`}
                title="驳回贡献"
              >
                <X size={17} /> 驳回
              </button>
            </div>
          </article>
        ))}
      </div>
      <div className="reviewGroup">
        <h3>待审核笔记</h3>
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
      </div>
    </section>
  );
}

function SystemOverview({ stats, onImport, busy }: { stats: Stats | null; onImport: () => void; busy: boolean }) {
  const cards = [
    ["课程", stats?.courses ?? 0, BookOpen],
    ["知识点", stats?.knowledge_points ?? 0, Layers],
    ["内容单元", stats?.content_units ?? 0, FileText],
    ["待审核笔记", stats?.pending_notes ?? 0, Check],
    ["已合并笔记", stats?.approved_notes ?? 0, Upload],
    ["个人空间", stats?.personal_spaces ?? 0, Database],
    ["待审核贡献", stats?.pending_contributions ?? 0, ShieldCheck],
    ["已合并贡献", stats?.approved_contributions ?? 0, Upload],
    ["社区内容", stats?.community_content_units ?? 0, Layers],
    ["问答记录", stats?.qa_logs ?? 0, MessageSquare]
  ] as const;
  return (
    <section className="systemOverview">
      <div className="adminPanel">
        <div>
          <h2>演示数据管理</h2>
          <p>这里保留导入和统计能力，面向管理员或比赛演示操作者。</p>
        </div>
        <button className="primary" onClick={onImport} disabled={busy} title="导入样例知识库">
          {busy ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
          从已有解析结果导入第 5 章 5.1-5.2
        </button>
      </div>
      <div className="statsGrid">
        {cards.map(([label, value, Icon]) => (
          <div className="metric" key={label}>
            <Icon size={20} />
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
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
          <p>复用现有 PDF → Markdown 能力。完整《微积分 II》已产出 `merged_full.md`，避免现场解析耗时。</p>
        </div>
        <div>
          <FlaskConical size={24} />
          <strong>text_archiver</strong>
          <p>已通过 DeepSeek 官方 API 完整清洗《微积分 II》，生成 `merged_full_formatted.md`，并作为 demo 优先导入源。</p>
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
