# Codex 接手规则

## 1. 项目目标简介

Owlsome Learning 是一个 AI 交互式数学学习平台，目标是把教材、PDF、讲义、题库和个人笔记转换成可拆解、可审核、可问答、可跟踪进度的学习空间。

当前项目采用“私人学习空间 + 公共知识库 + 可选贡献审核”的结构：

- 私人学习空间：用户上传资料、笔记、错题和学习进度默认属于个人。
- 公共知识库：用户主动贡献的笔记、题解或讲解，经审核后进入公共库。
- Demo 主线：公共教材导入、个人学习空间、贡献审核、问答和练习/错题闭环。

## 2. 主要目录说明

- `learning_platform/`：当前主 Demo，采用 FastAPI + React + SQLite。
- `learning_platform/backend/`：FastAPI 后端、SQLite schema、导入脚本、问答、贡献、练习等服务。
- `learning_platform/frontend/`：Vite + React + TypeScript 前端页面和样式。
- `learning_platform/sample_data/`：可离线演示的 Markdown 样例数据。
- `mineru_tools/`：PDF / 文档解析工具链，负责 PDF 转 Markdown。
- `text_archiver/`：Markdown 清洗工具，负责断行、标题层级、格式和 Obsidian 兼容增强。
- `owlsome_core/`：共享的 Obsidian-compatible Markdown 规范化能力。
- `docs/`：项目文档、设计系统、交接说明、演示脚本、测试记录和部署说明。

## 3. 前后端启动命令

后端启动：

```powershell
cd C:\Users\guagua\Desktop\Owlsome-main\learning_platform\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端健康检查：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health
```

前端启动：

```powershell
cd C:\Users\guagua\Desktop\Owlsome-main\learning_platform\frontend
npm install
npm run dev
```

浏览器访问：

```text
http://127.0.0.1:5173
```

## 4. 修改代码时的约束

- 不要破坏现有 demo 流程。
- 不要随意删除已有功能、脚本、样例数据或文档。
- 不要引入复杂的新依赖，除非确实必要并已说明原因。
- 保持 FastAPI + React + SQLite 的现有架构。
- 前端优先保持 Vite / React / TypeScript 的现有写法。
- 后端 API 命名和数据结构应尽量兼容现有前端与文档。
- 修改数据库 schema 时使用兼容式迁移，例如 `CREATE TABLE IF NOT EXISTS`，避免破坏已有 SQLite demo 数据。
- LLM、MinerU、BGE 检索都必须保持可选；离线 demo 应继续可用。
- 管理员模式目前是 demo 级隔离，不要误写成完整生产权限系统。
- 如果发现 README、docs 和代码不一致，先说明不一致点，再决定如何修。

## 5. UI 风格要求

UI 必须遵循 `docs/design_system.md`：

- 使用南大紫作为主色，金色只作为克制的辅助强调。
- 阅读区保持明亮、低噪声，突出数学内容和公式。
- 卡片圆角原则上不超过 8px，除非已有设计系统另有约定。
- 保持可访问性：按钮文字对比度足够，焦点轮廓可见，不只依赖颜色表达状态。
- 学习者页面和管理员页面要保持角色边界，避免把审核/系统管理功能暴露给普通学习者。
- 公共资源库和个人学习空间应优先服务资源树、知识点详情、问答、进度和贡献闭环，不做营销式首页。

## 6. 每次修改后的验证要求

根据改动范围选择验证项，优先保证 demo 主线可跑：

后端基础检查：

```powershell
cd C:\Users\guagua\Desktop\Owlsome-main
python -m compileall C:\Users\guagua\Desktop\Owlsome-main\learning_platform\backend\app C:\Users\guagua\Desktop\Owlsome-main\learning_platform\backend\scripts
```

后端 smoke test：

```powershell
cd C:\Users\guagua\Desktop\Owlsome-main\learning_platform\backend
python scripts\smoke_test.py
```

管理员 token 保护检查：

```powershell
cd C:\Users\guagua\Desktop\Owlsome-main\learning_platform\backend
python scripts\admin_guard_test.py
```

前端构建检查：

```powershell
cd C:\Users\guagua\Desktop\Owlsome-main\learning_platform\frontend
npm run build
```

浏览器手动检查：

- 访问 `http://127.0.0.1:5173`。
- 学习者模式应隐藏审核中心、系统概览、题目管理。
- 管理员模式应能看到审核中心、系统概览、题目管理。
- 公共资源库、个人学习空间、贡献审核、问答和练习反馈主流程应正常。
- Markdown callout、wikilink、高亮和 LaTeX 公式应正常渲染。

注意：`seed_demo.py --all` 会备份并重建 SQLite 数据库。运行前必须确认这是当前任务需要的操作。

## 7. Demo 流程保护

不得破坏以下稳定演示路径：

1. 管理员导入样例或全书资源。
2. 学习者浏览公共知识库。
3. 学习者创建或上传个人学习空间。
4. 学习者进行个人问答与进度标记。
5. 学习者主动申请贡献到公共库。
6. 管理员审核贡献或笔记。
7. 审核通过后，公共知识点详情显示社区贡献。
8. 题目绑定知识点后，学习者可记录做对、做错或不确定，并在工作台看到错题/薄弱点反馈。

## 8. 依赖管理

- 不要引入不必要的新依赖。
- 如果必须新增依赖，优先选择轻量、维护活跃、与现有栈兼容的库。
- 新依赖必须写入对应的 `requirements.txt` 或 `package.json`，并说明引入原因。
- 不要把 `node_modules/`、`dist/`、`.env`、SQLite 数据库、MinerU 输出等生成物作为源码提交。

## 9. 交付说明

每次修改完成后，必须用中文总结：

- 修改了哪些文件。
- 为什么要改。
- 如何验证。
- 哪些验证已运行，哪些未运行以及原因。
- 如果存在 README/docs 与代码不一致，说明当前处理方式和后续建议。
