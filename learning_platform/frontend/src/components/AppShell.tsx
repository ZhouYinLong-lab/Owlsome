import { BarChart3, BookOpen, Dumbbell, FlaskConical, FolderTree, Home, Loader2, Play, ShieldCheck, UserRound } from "lucide-react";
import { useState, type ReactNode } from "react";
import { readAdminToken, writeAdminToken } from "../api";
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
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [tokenInput, setTokenInput] = useState(readAdminToken() ?? "");

  function handleRoleToggle() {
    if (role === "learner") {
      // Switching to admin — show token input if not already stored
      const stored = readAdminToken();
      if (stored === null) {
        setTokenInput("");
        setShowTokenInput(true);
        return;
      }
    }
    onRoleChange(role === "admin" ? "learner" : "admin");
  }

  function confirmToken() {
    writeAdminToken(tokenInput.trim());
    setShowTokenInput(false);
    onRoleChange("admin");
  }
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
              <button className={tab === "exercises" ? "active" : ""} onClick={() => onTabChange("exercises")} title="题目管理">
                <Dumbbell size={18} /> 题目管理
              </button>
            </>
          )}
        </nav>
        <div className="roleSwitch" aria-label="本地演示角色切换">
          <span>{role === "admin" ? "管理员模式" : "学习者模式"}</span>
          {showTokenInput ? (
            <div className="tokenInputGroup">
              <input
                className="tokenInput"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="输入管理员 token（留空则无保护）"
                aria-label="管理员 token"
                onKeyDown={(e) => { if (e.key === "Enter") confirmToken(); }}
              />
              <div className="tokenInputActions">
                <button className="ghostButtonSmall" onClick={confirmToken}>
                  确认并切换
                </button>
                <button className="ghostButtonSmall" onClick={() => { setShowTokenInput(false); onRoleChange("admin"); }}>
                  跳过
                </button>
              </div>
            </div>
          ) : (
            <button onClick={handleRoleToggle}>
              {role === "admin" ? <UserRound size={16} /> : <ShieldCheck size={16} />}
              切换为{role === "admin" ? "学习者" : "管理员"}
            </button>
          )}
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
