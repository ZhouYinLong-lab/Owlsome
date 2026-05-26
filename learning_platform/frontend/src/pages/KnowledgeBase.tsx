import { useEffect, useMemo, useState } from "react";
import { BookOpen, FolderTree, HelpCircle, Layers, Loader2, MessageSquare, RefreshCw, Send, Upload } from "lucide-react";
import { api } from "../api";
import { InlineMarkdown, Markdown } from "../components/MarkdownRenderer";
import type { KnowledgePoint, KnowledgePointDetail } from "../types";
import { sourceLabel, unitLabel } from "../utils/labels";

function groupPointsByChapter(points: KnowledgePoint[]) {
  const groups = new Map<string, KnowledgePoint[]>();
  for (const point of points) {
    const chapter = point.chapter_title || "未分章资源";
    groups.set(chapter, [...(groups.get(chapter) ?? []), point]);
  }
  return [...groups.entries()].map(([chapter, chapterPoints]) => ({ chapter, points: chapterPoints }));
}

export function KnowledgeBase(props: {
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
