# Codex 工作记录

本文件用于记录 Codex 接手 Owlsome Learning 后的每轮修改，便于后续 agent 或队友快速理解改动背景、涉及文件、验证方式和下一步建议。

时间按本地时区 `Asia/Shanghai` 记录。早前轮次根据当前会话顺序整理；后续轮次请在文件末尾继续追加。

## 2026-05-31 早前 - 新增 Codex 接手规则

### 背景

为方便后续 Codex 或其他 agent 继续接手项目，需要在项目根目录放置统一工作规则。

### 修改文件

- `AGENTS.md`

### 主要内容

- 记录项目目标：AI 交互式数学学习平台，采用“私人学习空间 + 公共知识库 + 可选贡献审核”结构。
- 记录主要目录、前后端启动命令、修改约束、UI 风格要求和验证要求。
- 明确不允许破坏现有 demo 流程，不引入不必要新依赖。
- 明确每次修改后必须用中文总结改动和验证方式。

### 验证

- 已确认文件创建完成，内容覆盖用户要求的 9 项规则。

## 2026-05-31 早前 - 第一阶段：修复明显问题并提升首页/主流程演示效果

### 背景

根据 README 和 docs 中描述的 demo 流程，优先修复影响首页、公共知识库、个人空间和 TypeScript 检查的问题，避免大规模重构。

### 修改文件

- `learning_platform/frontend/package.json`
- `learning_platform/frontend/package-lock.json`
- `learning_platform/frontend/src/vite-env.d.ts`
- `learning_platform/frontend/src/App.tsx`
- `learning_platform/frontend/src/pages/Dashboard.tsx`
- `learning_platform/frontend/src/pages/KnowledgeBase.tsx`
- `learning_platform/frontend/src/pages/PersonalSpaces.tsx`

### 主要改动

- 补充 React/Vite 类型依赖与 `vite-env.d.ts`，修复前端 TypeScript 检查问题。
- 进入个人学习空间时自动加载已有空间，减少空白状态。
- 首页公共库为空时增加更明确的导入提示；管理员可从首页导入样例。
- 公共资源库空状态和笔记提交后的反馈更贴近 README demo 主线。
- 个人空间列表搜索的类型收窄修复，避免 TS noEmit 报错。

### 验证

- `npm exec tsc -- --noEmit` 通过。
- `npm run build` 通过，仅有 Vite CJS deprecation 和 chunk size 警告。
- `python -m compileall learning_platform/backend/app learning_platform/backend/scripts` 通过。
- 使用 `D:\Miniconda3\envs\owlsome\python.exe scripts\smoke_test.py`，14 项通过，0 失败。
- 通过 TestClient 验证笔记创建和审核合并流程。
- 浏览器手动核对了工作台、公共资源库、个人空间和错题/薄弱点展示。

## 2026-05-31 21:52 +08:00 - 第一优先级：补齐稳定演示数据准备

### 背景

README 描述的核心 demo 包含公共库、个人空间、笔记审核、贡献审核、练习绑定、错题和薄弱点闭环。原 `seed_demo.py --all` 只稳定准备了公共库、个人空间和贡献数据，比赛展示仍依赖手动操作或 smoke test 遗留数据。

### 修改文件

- `learning_platform/backend/scripts/seed_demo.py`
- `learning_platform/README.md`

### 主要改动

- 扩展 `seed_demo.py --all`，现在会准备：
  - 公共知识库样例。
  - 个人样例学习空间。
  - 已掌握、学习中、疑难点进度样例。
  - 1 条待审核笔记。
  - 1 条已审核并合并的笔记。
  - 1 条待审核贡献。
  - 1 条已审核并合并为社区内容的贡献。
  - 1 道已绑定到知识点的演示练习。
  - 1 条 wrong 练习记录，用于工作台错题和薄弱知识点展示。
- 新增可单独运行的 seed 参数：
  - `--learning-progress`
  - `--pending-note`
  - `--approved-note`
  - `--exercise-loop`
- 当 SQLite 数据库被正在运行的后端占用时，`--all` 会给出清晰中文提示，而不是直接输出 raw traceback。
- 更新 `learning_platform/README.md` 的“准备演示数据”说明，使文档与新 seed 行为一致。

### 验证

- `python -m compileall learning_platform/backend/app learning_platform/backend/scripts` 通过。
- `D:\Miniconda3\envs\owlsome\python.exe scripts\seed_demo.py --help` 正常显示新增参数。
- 当前后端占用 SQLite 时，`scripts\seed_demo.py --all` 会提示先停止 `uvicorn`。
- 在不重置数据库的情况下运行以下命令成功：

```powershell
python scripts\seed_demo.py --import-sample --personal-space --learning-progress --pending-note --approved-note --pending-contribution --approved-contribution --exercise-loop
```

- 只读数据库断言通过，当前运行数据包含：
  - `knowledge_points = 8`
  - `pending_notes = 1`
  - `approved_notes = 2`
  - `pending_contributions = 1`
  - `approved_contributions = 1`
  - `community_units = 1`
  - `linked_exercises = 2`
  - `mistakes = 2`
  - `weak_points = 2`
- 运行中的 API 只读检查通过：
  - `GET /api/stats`
  - `GET /api/contributions/pending`
  - `GET /api/exercises/weak-points`

### 后续建议

- 下一小步建议处理“微积分 II 全书导入源文件缺失”的前后端兜底提示。
- 再下一步建议补齐审核中心的贡献目标知识点人工改选能力。

## 2026-05-31 21:52 +08:00 - 新增 Codex 工作日志

### 背景

用户要求新增一份专门的工作记录文件，把每轮 Codex 修改记录按时间追加进去。

### 修改文件

- `docs/agent_work_log.md`

### 主要改动

- 新建本文件。
- 按时间顺序整理当前会话内已完成的三轮修改：
  - 新增 `AGENTS.md`。
  - 第一阶段前端与主流程演示修复。
  - 第一优先级 seed demo 数据补齐。
- 建立后续追加格式：背景、修改文件、主要改动、验证、后续建议。

### 验证

- 文件已创建；本条记录将在创建后通过读取文件确认。
