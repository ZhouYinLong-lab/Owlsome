import { FileText, FlaskConical, Layers } from "lucide-react";

export function Pipeline() {
  return (
    <section className="pipeline">
      <h2>资料处理链路</h2>
      <div className="pipelineGrid">
        <div>
          <FileText size={24} />
          <strong>mineru_tools</strong>
          <p>复用现有 PDF → Markdown 能力。完整《微积分 II》已产出 `merged_full.md`，避免现场解析耗时。</p>
        </div>
        <div>
          <FlaskConical size={24} />
          <strong>text_archiver</strong>
          <p>已通过 DeepSeek 官方 API 完整清洗《微积分 II》，生成 `merged_full_formatted.md`，并作为 demo 优先导入源。</p>
        </div>
        <div>
          <Layers size={24} />
          <strong>learning_platform</strong>
          <p>新增规则切分、SQLite 存储、公共知识库、个人学习空间、进度标记与问答展示。</p>
        </div>
      </div>
    </section>
  );
}
