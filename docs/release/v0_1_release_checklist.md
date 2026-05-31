# Owlsome Learning v0.1 Release Checklist

本文档用于 v0.1 可上线测试版的发布前验证。按顺序逐项执行，全部通过后即可交付。

## 1. 目标范围

将当前 Owlsome Learning demo 收敛为 v0.1 可上线测试版本。本轮重点是：

- 启动稳定、配置清晰、部署可复现。
- 核心闭环不回退。

### v0.1 包含的功能

1. 公共资源库浏览（按章节树 + 搜索 + 面包屑）
2. 微积分 II 全书导入（清洗版 `merged_full_formatted.md`）
3. 个人 Markdown 学习空间（上传 / 样例创建 + 进度 + 个人问答）
4. 当前知识点问答（离线回退 + 可选 LLM 增强）
5. 私人内容申请贡献
6. 管理员审核（笔记审核 + 贡献审核）
7. 社区贡献展示

### v0.1 明确不包含的功能

- 登录系统 / 真实权限控制（管理员模式只是前端演示隔离）
- 向量数据库 / BGE 检索（默认关闭，可选启用但不要求）
- 在线 PDF 实时解析（使用已有 MinerU Markdown 样例）
- UI 大改 / 大型新功能
- Docker 部署 / PostgreSQL 迁移
- 题目-知识点高精度关联（已实现基础版）
- 错题与薄弱点闭环（已实现 MVP，含工作台展示与跳转复习）

## 2. 必跑命令

以下命令必须在发布前全部通过。所有 `cd` 使用绝对路径。

### 2.1 后端编译检查

```powershell
cd D:\Projects\EL\learning_platform\backend
python -m compileall D:\Projects\EL\learning_platform\backend\app D:\Projects\EL\learning_platform\backend\scripts
```

期望：无 SyntaxError，exit code 0。

### 2.2 后端 Smoke Test

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\smoke_test.py
```

期望：每个检查项输出 `ok`，exit code 0。

### 2.3 准备演示数据（Seed）

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\seed_demo.py --all
```

期望：输出包含 "Seed complete" 或等价确认。数据库被备份并重建。

### 2.4 微积分 II 全书 Dry-Run

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\import_calculus_full.py --dry-run --report D:\Projects\EL\docs\test_records\calculus_full_import_report.md
```

期望：输出章节、知识点和内容单元统计，生成 Markdown 报告，不写入 SQLite。

### 2.5 内容 QA 审计

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\content_quality_audit.py --report D:\Projects\EL\docs\test_records\calculus_content_quality_audit.md
```

期望：生成 QA 报告，标记过长、过短、公式符号疑似不平衡或 marker 识别不足的知识点。

### 2.6 前端构建

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm run build
```

期望：`dist` 目录生成成功，无编译错误。

如果 `dist` 被占用：

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm run build -- --outDir dist_check
```

### 2.7 Git 状态检查

```powershell
cd D:\Projects\EL
git status --short
```

**确认不要出现以下文件：**
- `.env`
- `*.db`
- `*.db.bak`
- `dist`
- `dist_check`
- `node_modules`
- `mineru_tools/output`

## 3. 手动验收路径

### 路径 A：教材导入 → 公共资源浏览

1. 启动后端：`cd D:\Projects\EL\learning_platform\backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
2. 启动前端：`cd D:\Projects\EL\learning_platform\frontend && npm run dev`
3. 打开 `http://127.0.0.1:5173`
4. 点击"一键导入样例"
5. 进入"公共知识库"，确认能看到第 5 章知识点树
6. 点击知识点详情，确认讲解、定义、定理、例题、习题正常展示
7. 使用搜索框搜索章节标题、知识点编号或标题，确认过滤正常
8. 确认详情页顶部面包屑显示正确

### 路径 B：个人资料 → 私人学习空间 → 问答

1. 进入"个人学习空间"
2. 点击"用样例创建个人空间"
3. 确认生成个人知识点目录
4. 点击知识点，确认详情正常展示
5. 在"当前个人资料问答"中输入问题，确认有回答返回
6. 修改知识点状态（学习中 / 已掌握 / 疑难点），确认进度统计更新

### 路径 C：私人笔记 → 申请贡献 → 审核 → 公共库更新

1. 在个人知识点详情页点击"申请贡献到公共库"
2. 切换到管理员模式
3. 进入"审核中心"，确认能看到刚提交的贡献
4. 点击"通过"，确认审核完成
5. 切回学习者模式，进入公共知识库对应知识点
6. 确认已合并的社区贡献标签可见

## 4. 上线前安全检查

- [ ] `git status` 中没有 `.env`
- [ ] `git status` 中没有 `*.db`
- [ ] `git status` 中没有 `dist`
- [ ] `git status` 中没有 `node_modules`
- [ ] `git status` 中没有 `mineru_tools/output`
- [ ] README 明确说明管理员模式不是安全权限（仅前端演示隔离）
- [ ] `.env.example` 不包含真实 API Key
- [ ] 前端 `.env.example` 只包含默认 `http://127.0.0.1:8000`
- [ ] 后端 `.env.example` 所有 Key 字段留空

## 5. 失败回滚方案

### 数据库回滚

如果 `seed_demo.py --all` 或 `import_calculus_full.py --import` 出错：

1. 停止后端 uvicorn
2. 恢复备份数据库：
   ```powershell
   cd D:\Projects\EL\learning_platform\backend\data
   Copy-Item -Path learning_platform.db.bak -Destination learning_platform.db -Force
   ```
3. 重新运行 seed 或导入命令

### 前端构建回滚

如果 `npm run build` 失败：

1. 确认 `npm install` 已完成且无报错
2. 检查 `dist` 是否被占用（参考 README FAQ）
3. 删除 `node_modules` 并重装：
   ```powershell
   cd D:\Projects\EL\learning_platform\frontend
   Remove-Item -LiteralPath node_modules -Recurse -Force
   npm install
   npm run build
   ```

### 完整重置

如果环境出现不可恢复的问题：

```powershell
cd D:\Projects\EL
git checkout -- .
git clean -fd
```

然后从 README 第 1 步重新开始。

## 6. 交付物列表

| 交付物 | 路径 | 说明 |
|---|---|---|
| 后端代码 | `learning_platform/backend/app/` | FastAPI 应用 |
| 后端脚本 | `learning_platform/backend/scripts/` | seed、import、QA、smoke_test |
| 前端代码 | `learning_platform/frontend/src/` | React + Vite UI |
| 后端环境变量模板 | `learning_platform/backend/.env.example` | LLM / BGE 配置说明 |
| 前端环境变量模板 | `learning_platform/frontend/.env.example` | API 地址配置 |
| 项目 README | `README.md` | 完整操作指南 |
| 学习平台 README | `learning_platform/README.md` | 启动与演示说明 |
| Agent 接手指南 | `docs/agent_handoff_guide.md` | 架构与安全修改规则 |
| 实现概览 | `docs/implementation_overview.md` | 模块边界与 API 清单 |
| v0.1 发布检查清单 | `docs/release/v0_1_release_checklist.md` | 本文档 |
| Smoke Test | `learning_platform/backend/scripts/smoke_test.py` | 后端 API 快速验证（含 exercise + mistake/weak-point 端点，共 14 项） |
| Stage 4 MVP | `docs/stage4/exercise_knowledge_linking_mvp.md` | 题目-知识点挂钩 MVP |
| Stage 4 闭环节 | `docs/stage4/mistake_weakness_loop_mvp.md` | 错题与薄弱点闭环 MVP |
| Demo 路径 | `docs/demo/demo_paths.md` | 比赛演示路径 |
| Demo 脚本 | `docs/demo/competition_demo_script_5min.md` | 5 分钟演示脚本 |
| 样例数据 | `learning_platform/sample_data/` | 仓库内置 Markdown 样例 |

## 7. 建议提交信息

```
Prepare v0.1 test release workflow
```

提交内容：代码、README、`.env.example`、docs、脚本。
不提交：数据库、构建产物、API Key、大型生成文件。
