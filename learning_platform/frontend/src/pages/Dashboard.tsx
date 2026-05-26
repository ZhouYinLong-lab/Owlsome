import { Check, FolderTree, ShieldCheck, UserRound } from "lucide-react";
import type { KnowledgePoint, PersonalSpace, Stats, Tab } from "../types";

export function Dashboard({ stats, spaces, points, onNavigate }: {
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
