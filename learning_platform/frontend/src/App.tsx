import { useEffect, useState } from "react";
import { API_BASE, adminApi, api } from "./api";
import { AppShell } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { KnowledgeBase } from "./pages/KnowledgeBase";
import { PersonalSpaces } from "./pages/PersonalSpaces";
import { Pipeline } from "./pages/Pipeline";
import { ReviewCenter } from "./pages/ReviewCenter";
import { ExerciseManager } from "./pages/ExerciseManager";
import { SystemOverview } from "./pages/SystemOverview";
import type {
  CalculusFullImportResult,
  Contribution,
  KnowledgePoint,
  KnowledgePointDetail,
  Note,
  PersonalPoint,
  PersonalSpace,
  PersonalSpaceDetail,
  Role,
  Stats,
  Tab
} from "./types";

const STORAGE_KEYS = {
  role: "owlsome.role",
  tab: "owlsome.tab",
  publicKnowledgePointId: "owlsome.publicKnowledgePointId",
  personalSpaceId: "owlsome.personalSpaceId",
  personalPointId: "owlsome.personalPointId"
} as const;

const ADMIN_ONLY_TABS = new Set<Tab>(["review", "system", "exercises"]);
const VALID_TABS = new Set<Tab>(["dashboard", "knowledge", "personal", "pipeline", "review", "system", "exercises"]);
const VALID_ROLES = new Set<Role>(["learner", "admin"]);

function readStoredValue(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStoredValue(key: string, value: string | number) {
  try {
    window.localStorage.setItem(key, String(value));
  } catch {
    // Local storage is a demo convenience, not a required runtime dependency.
  }
}

function readStoredNumber(key: string): number | null {
  const value = readStoredValue(key);
  if (!value) return null;
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function initialRole(): Role {
  const stored = readStoredValue(STORAGE_KEYS.role);
  return stored && VALID_ROLES.has(stored as Role) ? stored as Role : "learner";
}

function initialTab(role: Role): Tab {
  const stored = readStoredValue(STORAGE_KEYS.tab);
  const tab = stored && VALID_TABS.has(stored as Tab) ? stored as Tab : "dashboard";
  return role === "learner" && ADMIN_ONLY_TABS.has(tab) ? "dashboard" : tab;
}

export function App() {
  const [role, setRole] = useState<Role>(() => initialRole());
  const [tab, setTab] = useState<Tab>(() => initialTab(initialRole()));
  const [stats, setStats] = useState<Stats | null>(null);
  const [points, setPoints] = useState<KnowledgePoint[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(() => readStoredNumber(STORAGE_KEYS.publicKnowledgePointId));
  const [detail, setDetail] = useState<KnowledgePointDetail | null>(null);
  const [personalSpaces, setPersonalSpaces] = useState<PersonalSpace[]>([]);
  const [selectedSpaceId, setSelectedSpaceId] = useState<number | null>(() => readStoredNumber(STORAGE_KEYS.personalSpaceId));
  const [personalSpace, setPersonalSpace] = useState<PersonalSpaceDetail | null>(null);
  const [selectedPersonalPointId, setSelectedPersonalPointId] = useState<number | null>(() => readStoredNumber(STORAGE_KEYS.personalPointId));
  const [personalPoint, setPersonalPoint] = useState<PersonalPoint | null>(null);
  const [pending, setPending] = useState<Note[]>([]);
  const [pendingContributions, setPendingContributions] = useState<Contribution[]>([]);
  const [fullImportResult, setFullImportResult] = useState<CalculusFullImportResult | null>(null);
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
    const requestedId = nextSelectedId ?? selectedId;
    const targetId = requestedId && nextPoints.some((point) => point.id === requestedId)
      ? requestedId
      : nextPoints[0]?.id ?? null;
    setSelectedId(targetId);
    if (targetId) {
      setDetail(await api<KnowledgePointDetail>(`/api/knowledge-points/${targetId}`));
    } else {
      setDetail(null);
    }

    const requestedSpaceId = selectedSpaceId ?? readStoredNumber(STORAGE_KEYS.personalSpaceId);
    const targetSpaceId = requestedSpaceId && nextSpaces.some((space) => space.id === requestedSpaceId)
      ? requestedSpaceId
      : nextSpaces[0]?.id ?? null;
    if (targetSpaceId && (tab === "personal" || selectedSpaceId)) {
      await loadPersonalSpace(targetSpaceId, selectedPersonalPointId ?? readStoredNumber(STORAGE_KEYS.personalPointId));
    }
  }

  async function loadPersonalSpace(spaceId: number, pointId?: number | null) {
    const space = await api<PersonalSpaceDetail>(`/api/personal-spaces/${spaceId}`);
    setSelectedSpaceId(spaceId);
    setPersonalSpace(space);
    const requestedPointId = pointId ?? selectedPersonalPointId;
    const targetPointId = requestedPointId && space.points.some((point) => point.id === requestedPointId)
      ? requestedPointId
      : space.points[0]?.id ?? null;
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
    if (role === "learner" && (tab === "review" || tab === "system" || tab === "exercises")) {
      setTab("dashboard");
    }
  }, [role, tab]);

  useEffect(() => {
    writeStoredValue(STORAGE_KEYS.role, role);
  }, [role]);

  useEffect(() => {
    writeStoredValue(STORAGE_KEYS.tab, tab);
  }, [tab]);

  useEffect(() => {
    if (selectedId) writeStoredValue(STORAGE_KEYS.publicKnowledgePointId, selectedId);
  }, [selectedId]);

  useEffect(() => {
    if (selectedSpaceId) writeStoredValue(STORAGE_KEYS.personalSpaceId, selectedSpaceId);
  }, [selectedSpaceId]);

  useEffect(() => {
    if (selectedPersonalPointId) writeStoredValue(STORAGE_KEYS.personalPointId, selectedPersonalPointId);
  }, [selectedPersonalPointId]);

  async function importSample() {
    setBusy("import");
    try {
      const result = await adminApi<{ message: string }>("/api/import/sample", { method: "POST" });
      setMessage(result.message);
      await refreshAll();
      setTab("knowledge");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "导入失败");
    } finally {
      setBusy("");
    }
  }

  async function importCalculusFull(dryRun: boolean) {
    setBusy(dryRun ? "calculus-full-dry-run" : "calculus-full-import");
    try {
      const result = await adminApi<CalculusFullImportResult>("/api/import/calculus-full", {
        method: "POST",
        body: JSON.stringify({
          dry_run: dryRun,
          reset_course: !dryRun,
          write_report: true
        })
      });
      setFullImportResult(result);
      setMessage(result.message);
      if (!dryRun) {
        await refreshAll();
        setTab("knowledge");
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "微积分 II 全书导入失败");
    } finally {
      setBusy("");
    }
  }

  async function selectPoint(id: number) {
    setSelectedId(id);
    setDetail(await api<KnowledgePointDetail>(`/api/knowledge-points/${id}`));
  }

  async function openKnowledgePoint(id: number) {
    setTab("knowledge");
    setSelectedId(id);
    setDetail(await api<KnowledgePointDetail>(`/api/knowledge-points/${id}`));
  }

  async function continuePersonalLearning() {
    const targetSpaceId = selectedSpaceId ?? personalSpaces[0]?.id ?? null;
    if (targetSpaceId) {
      await loadPersonalSpace(targetSpaceId, selectedPersonalPointId);
    }
    setTab("personal");
  }

  async function approveNote(noteId: number) {
    setBusy(`approve-${noteId}`);
    await adminApi(`/api/notes/${noteId}/approve`, { method: "POST" });
    await refreshAll(selectedId);
    setBusy("");
  }

  async function rejectNote(noteId: number) {
    setBusy(`reject-${noteId}`);
    await adminApi(`/api/notes/${noteId}/reject`, { method: "POST" });
    await refreshAll(selectedId);
    setBusy("");
  }

  async function reviewContribution(contributionId: number, action: "approve" | "reject" | "request-revision") {
    setBusy(`${action}-contribution-${contributionId}`);
    await adminApi(`/api/contributions/${contributionId}/${action}`, {
      method: "POST",
      body: JSON.stringify({ comment: action === "approve" ? "审核通过，合并到公共知识库。" : "" })
    });
    await refreshAll(selectedId);
    setBusy("");
  }

  return (
    <AppShell
      role={role}
      tab={tab}
      busy={busy}
      message={message}
      onRoleChange={setRole}
      onTabChange={setTab}
      onImportSample={importSample}
    >
      {tab === "dashboard" && (
        <Dashboard
          stats={stats}
          spaces={personalSpaces}
          points={points}
          onNavigate={setTab}
          role={role}
          onOpenKnowledgePoint={openKnowledgePoint}
          onContinuePersonal={continuePersonalLearning}
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
        <ReviewCenter
          notes={pending}
          contributions={pendingContributions}
          busy={busy}
          onApprove={approveNote}
          onReject={rejectNote}
          onContributionAction={reviewContribution}
        />
      )}
      {tab === "system" && role === "admin" && (
        <SystemOverview
          stats={stats}
          onImport={importSample}
          onImportFull={() => importCalculusFull(false)}
          onDryRunFull={() => importCalculusFull(true)}
          busy={busy}
          fullImportResult={fullImportResult}
        />
      )}
      {tab === "exercises" && role === "admin" && <ExerciseManager />}
      {tab === "pipeline" && <Pipeline />}
    </AppShell>
  );
}
