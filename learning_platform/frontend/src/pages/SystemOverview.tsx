import { BookOpen, Check, Database, FileText, Layers, Loader2, MessageSquare, Play, ShieldCheck, Upload } from "lucide-react";
import type { CalculusFullImportResult, Stats } from "../types";

export function SystemOverview({
  stats,
  onImport,
  onImportFull,
  onDryRunFull,
  busy,
  fullImportResult
}: {
  stats: Stats | null;
  onImport: () => void;
  onImportFull: () => void;
  onDryRunFull: () => void;
  busy: string;
  fullImportResult: CalculusFullImportResult | null;
}) {
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
          <p>这里保留导入和统计能力，面向管理员或比赛演示操作者。章节样例适合快速演示，清洗版全书适合展示真实教材规模。</p>
        </div>
        <button className="primary" onClick={onImport} disabled={Boolean(busy)} title="导入样例知识库">
          {busy === "import" ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
          导入章节样例
        </button>
      </div>

      <div className="adminPanel fullImportPanel">
        <div>
          <h2>微积分 II 全书导入</h2>
          <p>从清洗版 Markdown 构建第 5–10 章公共资源库。真实导入会先重建同名课程，但不会删除个人空间和审核记录。</p>
          {fullImportResult && (
            <div className="importResult">
              <strong>{fullImportResult.imported ? "已写入公共资源库" : "结构检查完成"}</strong>
              <span>章节 {fullImportResult.chapters} · 知识点 {fullImportResult.knowledge_points} · 内容单元 {fullImportResult.content_units}</span>
              <small>输入源：{fullImportResult.input_path}</small>
              {fullImportResult.report_path && <small>报告：{fullImportResult.report_path}</small>}
            </div>
          )}
        </div>
        <div className="adminActions">
          <button className="ghostButton" onClick={onDryRunFull} disabled={Boolean(busy)} title="只生成报告不写入数据库">
            {busy === "calculus-full-dry-run" ? <Loader2 className="spin" size={18} /> : <FileText size={18} />}
            先做 dry-run
          </button>
          <button className="primary" onClick={onImportFull} disabled={Boolean(busy)} title="导入清洗版全书">
            {busy === "calculus-full-import" ? <Loader2 className="spin" size={18} /> : <Upload size={18} />}
            导入清洗版全书
          </button>
        </div>
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
