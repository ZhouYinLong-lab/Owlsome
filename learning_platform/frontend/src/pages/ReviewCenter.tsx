import { Check, RefreshCw, X } from "lucide-react";
import { Markdown } from "../components/MarkdownRenderer";
import type { Contribution, Note } from "../types";
import { contributionLabel } from "../utils/labels";

export function ReviewCenter({ notes, contributions, busy, onApprove, onReject, onContributionAction }: {
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
