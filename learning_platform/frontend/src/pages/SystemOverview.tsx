import { BookOpen, Check, Database, FileText, Layers, Loader2, MessageSquare, Play, ShieldCheck, Upload } from "lucide-react";
import type { Stats } from "../types";

export function SystemOverview({ stats, onImport, busy }: { stats: Stats | null; onImport: () => void; busy: boolean }) {
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
