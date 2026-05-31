import { useEffect, useState } from "react";
import { CheckCircle, Dumbbell, Link2, Loader2, Plus, Search, Target } from "lucide-react";
import { adminApi, api } from "../api";
import type { Exercise, ExerciseRecommendation } from "../types";

export function ExerciseManager() {
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [stem, setStem] = useState("");
  const [title, setTitle] = useState("");
  const [answer, setAnswer] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [difficulty, setDifficulty] = useState(2);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  // Recommendation state
  const [selectedExerciseId, setSelectedExerciseId] = useState<number | null>(null);
  const [recommendations, setRecommendations] = useState<ExerciseRecommendation[]>([]);
  const [linkedIds, setLinkedIds] = useState<Set<number>>(new Set());
  const [recommendReason, setRecommendReason] = useState("");

  useEffect(() => {
    loadExercises().catch((err) => {
      setMessage(err instanceof Error ? err.message : "题目列表加载失败");
    });
  }, []);

  async function loadExercises() {
    const list = await api<Exercise[]>("/api/exercises");
    setExercises(list);
  }

  async function createExercise() {
    if (!stem.trim()) {
      setMessage("题干不能为空。");
      return;
    }
    setBusy("create");
    try {
      const result = await adminApi<Exercise>("/api/exercises", {
        method: "POST",
        body: JSON.stringify({ title: title.trim(), stem: stem.trim(), answer, analysis, difficulty })
      });
      setMessage(`已创建题目 #${result.id}`);
      setTitle("");
      setStem("");
      setAnswer("");
      setAnalysis("");
      setDifficulty(2);
      await loadExercises();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "创建失败");
    } finally {
      setBusy("");
    }
  }

  async function recommend(exerciseId: number) {
    setSelectedExerciseId(exerciseId);
    setRecommendations([]);
    setLinkedIds(new Set());
    setBusy(`recommend-${exerciseId}`);
    try {
      const result = await api<{
        candidates: ExerciseRecommendation[];
        provider: string;
        fallback: boolean;
        reason: string;
      }>("/api/exercises/recommend", {
        method: "POST",
        body: JSON.stringify({ exercise_id: exerciseId, top_k: 3 })
      });
      setRecommendations(result.candidates);
      setRecommendReason(result.provider + (result.fallback ? " (fallback)" : ""));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "推荐失败");
    } finally {
      setBusy("");
    }
  }

  async function link(exerciseId: number, knowledgePointId: number) {
    setBusy(`link-${exerciseId}-${knowledgePointId}`);
    try {
      await adminApi(`/api/exercises/${exerciseId}/link`, {
        method: "POST",
        body: JSON.stringify({ knowledge_point_id: knowledgePointId, confidence: 1.0, reason: "管理员确认绑定" })
      });
      setLinkedIds((prev) => new Set(prev).add(knowledgePointId));
      setMessage(`已绑定知识点 #${knowledgePointId}`);
      await loadExercises();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "绑定失败");
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="exerciseManager">
      <div className="adminPanel">
        <div>
          <h2><Dumbbell size={20} /> 创建题目</h2>
          <p>录入题目后可使用推荐功能匹配知识点，再由管理员确认绑定。</p>
        </div>
      </div>

      <div className="toolPanel exerciseForm">
        <label>
          标题（可选）
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="例如：二重极限路径判断题" />
        </label>
        <label>
          题干 <span style={{ color: "var(--color-danger)" }}>*</span>
          <textarea value={stem} onChange={(e) => setStem(e.target.value)} placeholder="输入题目题干…" rows={4} />
        </label>
        <div style={{ display: "flex", gap: 12 }}>
          <label style={{ flex: 1 }}>
            答案（可选）
            <input value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="正确答案或解析提示" />
          </label>
          <label style={{ width: 100 }}>
            难度 1-5
            <input type="number" min={1} max={5} value={difficulty} onChange={(e) => setDifficulty(Number(e.target.value))} />
          </label>
        </div>
        <label>
          解析（可选）
          <textarea value={analysis} onChange={(e) => setAnalysis(e.target.value)} placeholder="解析说明…" rows={3} />
        </label>
        <button className="primary" onClick={createExercise} disabled={busy === "create"}>
          {busy === "create" ? <Loader2 className="spin" size={18} /> : <Plus size={18} />}
          创建题目
        </button>
      </div>

      {message && <div className="notice">{message}</div>}

      <div className="adminPanel" style={{ marginTop: 24 }}>
        <div>
          <h2><Search size={20} /> 已有题目</h2>
          <p>选择一个题目，点击"推荐知识点"查看 Top-3 匹配结果。</p>
        </div>
        <button className="ghostButton" onClick={loadExercises} title="刷新列表">
          刷新列表
        </button>
      </div>

      {exercises.length === 0 && (
        <p style={{ color: "var(--color-muted)", padding: "0 16px" }}>暂无题目，先创建一个。</p>
      )}

      {exercises.map((ex) => (
        <div className="toolPanel" key={ex.id} style={{ marginTop: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
            <div>
              <strong>#{ex.id} {ex.title || "未命名题目"}</strong>
              <span style={{ marginLeft: 8, fontSize: "0.85rem", color: "var(--color-muted)" }}>
                难度 {ex.difficulty} · {ex.status === "linked" ? <span style={{ color: "var(--color-success)" }}>已绑定</span> : "草稿"}
              </span>
            </div>
            <button
              className="ghostButton"
              onClick={() => recommend(ex.id)}
              disabled={busy === `recommend-${ex.id}`}
            >
              {busy === `recommend-${ex.id}` ? <Loader2 className="spin" size={16} /> : <Target size={16} />}
              推荐知识点
            </button>
          </div>
          <p style={{ whiteSpace: "pre-wrap", marginTop: 8 }}>{ex.stem}</p>
          {ex.answer && <p style={{ fontSize: "0.9rem", color: "var(--color-muted)" }}>答案：{ex.answer}</p>}

          {selectedExerciseId === ex.id && recommendations.length > 0 && (
            <div style={{ marginTop: 12, borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
              <small style={{ color: "var(--color-muted)" }}>匹配策略：{recommendReason}</small>
              {recommendations.map((rec) => {
                const alreadyLinked = linkedIds.has(rec.knowledge_point_id) || ex.status === "linked";
                return (
                  <div key={rec.knowledge_point_id} className="exerciseRecCandidate">
                    <div>
                      <strong>{rec.code}</strong> {rec.title}
                      <span style={{ marginLeft: 8, fontSize: "0.8rem", color: "var(--color-muted)" }}>
                        score={rec.score.toFixed(1)}
                      </span>
                      <br />
                      <small>{rec.reason}</small>
                    </div>
                    <button
                      className="primary"
                      onClick={() => link(ex.id, rec.knowledge_point_id)}
                      disabled={alreadyLinked || busy === `link-${ex.id}-${rec.knowledge_point_id}`}
                      style={{ fontSize: "0.85rem", padding: "4px 12px" }}
                    >
                      {busy === `link-${ex.id}-${rec.knowledge_point_id}` ? (
                        <Loader2 className="spin" size={16} />
                      ) : alreadyLinked ? (
                        <CheckCircle size={16} />
                      ) : (
                        <Link2 size={16} />
                      )}
                      {alreadyLinked ? "已绑定" : "确认绑定"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {selectedExerciseId === ex.id && recommendations.length === 0 && !busy && (
            <p style={{ marginTop: 8, color: "var(--color-muted)", fontSize: "0.9rem" }}>
              暂无推荐结果，请确认知识点库不为空。
            </p>
          )}
        </div>
      ))}
    </section>
  );
}
