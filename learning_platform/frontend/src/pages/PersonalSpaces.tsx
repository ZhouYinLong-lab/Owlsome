import { useEffect, useState } from "react";
import { FileText, Loader2, MessageSquare, Play, RefreshCw, Send, Upload } from "lucide-react";
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
