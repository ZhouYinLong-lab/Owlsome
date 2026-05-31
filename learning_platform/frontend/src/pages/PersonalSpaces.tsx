import { useEffect, useMemo, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  FileText,
  FolderTree,
  Loader2,
  MessageSquare,
  Play,
  RefreshCw,
  Search,
  Send,
  Upload
} from "lucide-react";
import { api } from "../api";
import { InlineMarkdown, Markdown } from "../components/MarkdownRenderer";
import type { Contribution, PersonalPoint, PersonalSpace, PersonalSpaceDetail, ProgressCounts } from "../types";
import { progressLabel, unitLabel } from "../utils/labels";

export function PersonalSpaces(props: {
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
  const [openSpaces, setOpenSpaces] = useState<Set<number>>(new Set());
  const [query, setQuery] = useState("");
  const [spaceCache, setSpaceCache] = useState<Record<number, PersonalSpaceDetail>>({});

  useEffect(() => {
    if (props.space) {
      setSpaceCache((current) => ({ ...current, [props.space.id]: props.space as PersonalSpaceDetail }));
    }
  }, [props.space]);

  useEffect(() => {
    const search = query.trim();
    if (!search || props.spaces.length === 0) return;
    let cancelled = false;
    async function loadMissingSpaces() {
      const missing = props.spaces.filter((space) => !spaceCache[space.id]);
      if (missing.length === 0) return;
      const details = await Promise.all(
        missing.map((space) =>
          api<PersonalSpaceDetail>(`/api/personal-spaces/${space.id}`).catch(() => null)
        )
      );
      if (cancelled) return;
      setSpaceCache((current) => {
        const next = { ...current };
        for (const detail of details) {
          if (detail) next[detail.id] = detail;
        }
        return next;
      });
    }
    loadMissingSpaces();
    return () => {
      cancelled = true;
    };
  }, [props.spaces, query, spaceCache]);

  const filteredSpaces = useMemo(() => props.spaces
      .map((space) => {
        const detail = spaceCache[space.id] ?? (props.selectedSpaceId === space.id ? props.space : null);
        const search = query.trim().toLowerCase();
        const spaceText = [space.title, space.source_file, space.source_type].join(" ").toLowerCase();
        const spaceMatches = search ? spaceText.includes(search) : true;
        const points = detail?.points ?? [];
        const matchingPoints = search
          ? points.filter((point) => {
            const pointText = [point.code, point.title, point.summary, point.tags].join(" ").toLowerCase();
            return pointText.includes(search);
          })
          : points;
        if (!search || spaceMatches) return { space, detail, points };
        if (matchingPoints.length > 0) return { space, detail, points: matchingPoints };
        return null;
      })
      .filter((item): item is { space: PersonalSpace; detail: PersonalSpaceDetail | null; points: PersonalPoint[] } => Boolean(item)),
    [props.spaces, props.selectedSpaceId, props.space, query, spaceCache]
  );

  useEffect(() => {
    setOpenSpaces((current) => {
      const next = new Set(current);
      if (props.selectedSpaceId) next.add(props.selectedSpaceId);
      if (!props.selectedSpaceId && props.spaces[0]) next.add(props.spaces[0].id);
      if (query.trim()) {
        for (const item of filteredSpaces) next.add(item.space.id);
      }
      return next;
    });
  }, [props.selectedSpaceId, props.spaces, filteredSpaces, query]);

  function toggleSpace(spaceId: number) {
    setOpenSpaces((current) => {
      const next = new Set(current);
      if (next.has(spaceId)) {
        next.delete(spaceId);
      } else {
        next.add(spaceId);
      }
      return next;
    });
  }

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
          <label className="resourceSearch">
            <Search size={16} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索资料、知识点、标签"
              aria-label="搜索个人学习空间"
            />
          </label>
          <div className="personalTree">
            {query.trim() && <small className="treeMeta">找到 {filteredSpaces.length} 个资料空间</small>}
            {filteredSpaces.map(({ space, points }) => (
              <div className="treeGroup personalSpaceGroup" key={space.id}>
                <button
                  className={props.selectedSpaceId === space.id ? "treeNode space selected" : "treeNode space"}
                  onClick={() => {
                    props.onSelectSpace(space.id);
                    toggleSpace(space.id);
                  }}
                >
                  {openSpaces.has(space.id) ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                  <FolderTree size={16} />
                  <span>{space.source_type}</span>
                  <strong><InlineMarkdown>{space.title}</InlineMarkdown></strong>
                </button>
                <small className="treeMeta">
                  {space.knowledge_point_count} 个知识点 · 已掌握 {space.progress.mastered}/{space.progress.total}
                </small>
                <div className={openSpaces.has(space.id) ? "treeChildren open" : "treeChildren"}>
                  {points.map((point) => (
                    <button
                      key={point.id}
                      className={props.selectedPointId === point.id ? "treePoint selected" : "treePoint"}
                      onClick={() => props.onSelectPoint(space.id, point.id)}
                    >
                      <span>{point.code}</span>
                      <strong><InlineMarkdown>{point.title}</InlineMarkdown></strong>
                      <small>{progressLabel(point.progress_status)} · {point.content_count ?? 0} 个内容单元</small>
                    </button>
                  ))}
                  {!query.trim() && props.selectedSpaceId !== space.id && (
                    <button className="treePoint placeholder" onClick={() => props.onSelectSpace(space.id)}>
                      展开后加载资料目录
                    </button>
                  )}
                  {query.trim() && points.length === 0 && (
                    <button className="treePoint placeholder" onClick={() => props.onSelectSpace(space.id)}>
                      匹配资料空间，点击加载目录
                    </button>
                  )}
                </div>
              </div>
            ))}
            {props.spaces.length === 0 && <div className="emptyState">还没有个人空间，先上传 Markdown 或使用样例。</div>}
            {props.spaces.length > 0 && filteredSpaces.length === 0 && (
              <div className="emptyState">没有匹配的个人资料或知识点。</div>
            )}
          </div>
        </div>
      </div>
      <PersonalSpaceDetailView
        space={props.space}
        point={props.point}
        selectedPointId={props.selectedPointId}
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
      <div className="personalWorkspace single">
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
  const [error, setError] = useState("");
  const [showContributionForm, setShowContributionForm] = useState(false);
  const [contributionTitle, setContributionTitle] = useState("");
  const [contributionType, setContributionType] = useState("note");

  useEffect(() => {
    setAnswer("");
    setHint("");
    setError("");
    setShowContributionForm(false);
    setContributionTitle(point?.title ?? "");
    setContributionType("note");
  }, [point?.id]);

  if (!point) {
    return <div className="detailPane empty">请选择一个个人知识点。</div>;
  }

  async function setProgress(status: string) {
    setError("");
    setBusy(status);
    try {
      await api(`/api/personal-spaces/${spaceId}/knowledge-points/${point?.id}/progress`, {
        method: "POST",
        body: JSON.stringify({ status })
      });
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "状态更新失败，请检查后端是否运行。");
    } finally {
      setBusy("");
    }
  }

  async function ask() {
    setError("");
    setBusy("personal-qa");
    try {
      const res = await api<{ answer: string; mode: string }>(`/api/personal-spaces/${spaceId}/qa`, {
        method: "POST",
        body: JSON.stringify({ personal_knowledge_point_id: point?.id, question })
      });
      setAnswer(`${res.answer}\n\n回答模式：${res.mode}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "问答请求失败，请检查后端是否运行。");
    } finally {
      setBusy("");
    }
  }

  async function submitContribution() {
    setError("");
    setBusy("contribution");
    try {
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "贡献提交失败，请检查后端是否运行。");
    } finally {
      setBusy("");
    }
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
      {error && <p className="attemptError">{error}</p>}
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
