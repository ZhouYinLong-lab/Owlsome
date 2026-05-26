import { BarChart3, BookOpen, FlaskConical, FolderTree, Home, Loader2, Play, ShieldCheck, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import type { Role, Tab } from "../types";
import { pageMeta } from "../utils/labels";

type AppShellProps = {
  role: Role;
  tab: Tab;
  busy: string;
  message: string;
  onRoleChange: (role: Role) => void;
  onTabChange: (tab: Tab) => void;
  onImportSample: () => void;
  children: ReactNode;
};

export function AppShell({ role, tab, busy, message, onRoleChange, onTabChange, onImportSample, children }: AppShellProps) {
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
          <button className={tab === "dashboard" ? "active" : ""} onClick={() => onTabChange("dashboard")} title="控制台">
            <Home size={18} /> 工作台
          </button>
          <button className={tab === "knowledge" ? "active" : ""} onClick={() => onTabChange("knowledge")} title="公共知识库">
            <FolderTree size={18} /> 公共资源库
          </button>
          <button className={tab === "personal" ? "active" : ""} onClick={() => onTabChange("personal")} title="个人学习空间">
            <UserRound size={18} /> 个人学习空间
          </button>
          <button className={tab === "pipeline" ? "active" : ""} onClick={() => onTabChange("pipeline")} title="资料处理">
            <FlaskConical size={18} /> 资料处理
          </button>
          {role === "admin" && (
            <>
              <div className="navDivider">管理员</div>
              <button className={tab === "review" ? "active" : ""} onClick={() => onTabChange("review")} title="审核中心">
                <ShieldCheck size={18} /> 审核中心
              </button>
              <button className={tab === "system" ? "active" : ""} onClick={() => onTabChange("system")} title="系统概览">
                <BarChart3 size={18} /> 系统概览
              </button>
            </>
          )}
        </nav>
        <div className="roleSwitch" aria-label="本地演示角色切换">
          <span>{role === "admin" ? "管理员模式" : "学习者模式"}</span>
          <button onClick={() => onRoleChange(role === "admin" ? "learner" : "admin")}>
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
            <button className="primary" onClick={onImportSample} disabled={busy === "import"} title="一键导入样例">
              {busy === "import" ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              一键导入样例
            </button>
          )}
        </header>

        {message && <div className="notice">{message}</div>}
        {children}
      </main>
    </div>
  );
}
