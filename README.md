# Owlsome Learning

Owlsome Learning 是 Owlsome Team（邪恶猫头鹰组）面向 EL 大赛交互组开发的 AI 交互式数学学习平台。项目目标是把静态教材、PDF、讲义、题库和个人笔记转换成可拆解、可审核、可问答、可跟踪进度的学习空间。

平台当前采用“私人学习空间 + 公共知识库 + 可选贡献审核”的双层知识结构：

- 私人学习空间：用户上传的资料、笔记、错题和学习进度默认只属于个人，用于个人问答、复习和进度管理。
- 公共知识库：用户主动选择贡献的笔记、题解或讲解，经自动化处理和审核后进入公共知识库，供后续学习者复用。

核心闭环：

```text
个人资料上传
→ 自动解析与清洗
→ 知识点拆分与匹配
→ 生成私人学习空间
→ 私人问答、练习、进度追踪
→ 用户选择是否贡献笔记/题解/讲解
→ 系统自动结构化与预审
→ 审核通过后合并进公共知识库
→ 后续学习者在公共知识库中复用
```

## 当前 Demo

当前仓库已经包含第一版可展示 demo：

- 公共教材知识库：从 MinerU Markdown 样例导入《微积分 II》第 5 章 `5.1-5.2`。
- 知识点结构化：自动拆分知识点、定义、定理、例题、习题。
- 笔记审核合并：学生笔记先进入审核区，审核通过后合并到知识点。
- 个人学习空间：支持上传 Markdown / TXT，生成个人知识点目录、详情、问答和进度。
- 可选贡献闭环：个人知识点可申请贡献到公共库，审核通过后合并为社区内容。
- Obsidian-compatible Markdown：支持 frontmatter、callout、wikilink、高亮和 LaTeX 公式渲染。
- 离线可演示：没有 LLM API Key 时也能完整跑通；配置 DeepSeek 或其他 OpenAI-compatible LLM 后可增强问答和清洗效果。

## 产品与 UI 协作

当前阶段的重点是把 demo 收束成更像真实产品的平台结构。团队协作时建议先阅读：

- `D:\Projects\EL\docs\README.md`：项目文档索引，适合新成员或新 agent 快速定位资料。
- `D:\Projects\EL\docs\agent_handoff_guide.md`：完整接手指南，包含架构、数据流、关键文件、运行命令和安全修改规则。
- `D:\Projects\EL\docs\design_system.md`：南大紫主题、可访问性规则和前端视觉约束。
- `D:\Projects\EL\docs\anyreader_reuse_strategy.md`：说明 AnyReader UI 中哪些阅读、锚点和高亮能力适合被 Owlsome 吸收。
- `D:\Projects\EL\docs\ui_collaboration_guide.md`：说明设计成员如何交付页面线框、状态图、组件清单和交互说明。

## 项目结构

```text
D:\Projects\EL
├─ learning_platform      # 当前主 Demo：FastAPI + React + SQLite
├─ mineru_tools           # PDF / 文档解析工具，负责 PDF -> Markdown
├─ owlsome_core           # Obsidian-compatible Markdown 规范化工具
├─ text_archiver          # Markdown 清洗工具，负责断行、标题、格式修复
├─ docs                   # 技术文档、版本策略和项目企划书
└─ 项目书_初稿.md          # 早期项目背景、路线图和 MVP 规划
```

## 环境要求

建议环境：

- Windows 10/11
- Python 3.10+
- Node.js 18+
- npm 9+
- Git

可选环境：

- DeepSeek/OpenAI-compatible API Key，用于 LLM 增强问答和 Markdown 清洗。
- MinerU 相关 token 或配置，用于真实 PDF 解析。第一版 demo 可直接使用仓库内已有 Markdown 样例，无需现场解析 PDF。
- Docker / Docker Compose，后续 Stage 5 用于一键部署和本地复现。

## 完整操作指南

以下命令均使用绝对路径，默认项目位于 `D:\Projects\EL`。

### 1. 获取仓库

如果本地还没有项目：

```powershell
cd D:\Projects
git clone https://github.com/ZhouYinLong-lab/Owlsome.git EL
```

如果本地已经有项目：

```powershell
cd D:\Projects\EL
git pull
```

### 2. 安装学习平台后端依赖

```powershell
cd D:\Projects\EL\learning_platform\backend
python -m pip install --upgrade pip
python -m pip install -r D:\Projects\EL\learning_platform\backend\requirements.txt
```

启动后端：

```powershell
cd D:\Projects\EL\learning_platform\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

健康检查：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health
```

期望返回：

```json
{"ok":true,"service":"learning_platform"}
```

### 3. 安装学习平台前端依赖

打开新的 PowerShell 窗口：

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm install
```

启动前端：

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm run dev
```

访问：

```text
http://127.0.0.1:5173
```

如果 `5173` 被占用，Vite 可能会切换到 `5174` 或其他端口；后端已经允许本地开发端口访问。

### 4. 安装 text_archiver 依赖

`text_archiver` 用于基于 LLM 清洗 Markdown，修复 PDF 转换后的断行、标题层级和格式问题。

```powershell
cd D:\Projects\EL\text_archiver
python -m pip install -r D:\Projects\EL\text_archiver\requirements.txt
```

复制环境变量示例：

```powershell
cd D:\Projects\EL\text_archiver
Copy-Item -Path D:\Projects\EL\text_archiver\.env.example -Destination D:\Projects\EL\text_archiver\.env
```

按需编辑 `D:\Projects\EL\text_archiver\.env`，配置 DeepSeek 或其他 OpenAI-compatible API。当前临时推荐配置：

```env
LLM_API_KEY=你的 DeepSeek Key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

旧的 `OPENROUTER_*` 与 `MODEL_NAME` 变量仍兼容。

运行样例清洗：

```powershell
cd D:\Projects\EL\text_archiver
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --obsidian
```

无 API Key 时可先 dry-run 验证分块和抽样：

```powershell
cd D:\Projects\EL
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --dry-run --parallel 4 --auto-profile --profile-samples 3 --report
```

并行清洗长文档：

```powershell
cd D:\Projects\EL\text_archiver
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --parallel 4 --auto-profile --profile-samples 5 --report
```

如果 API 触发速率限制，可降低并发并增大退避时间：

```powershell
cd D:\Projects\EL\text_archiver
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --parallel 2 --rate-limit-delay 5 --report
```

无 API Key 时，学习平台 demo 仍可完整演示；`text_archiver` 的在线清洗属于增强能力。

### 5. 安装 mineru_tools 依赖

`mineru_tools` 用于 PDF / 文档解析，目标是把 PDF 转成 Markdown。

```powershell
cd D:\Projects\EL\mineru_tools
python -m pip install -r D:\Projects\EL\mineru_tools\requirements_web.txt
```

如果只使用 MinerU client：

```powershell
cd D:\Projects\EL\mineru_tools\mineru_client
python -m pip install -r D:\Projects\EL\mineru_tools\mineru_client\requirements.txt
```

启动 MinerU WebUI：

```powershell
cd D:\Projects\EL\mineru_tools
python D:\Projects\EL\mineru_tools\run.py --host 127.0.0.1 --port 7861
```

访问：

```text
http://127.0.0.1:7861
```

第一版学习平台 demo 默认读取已有样例 Markdown，不要求现场启动 MinerU WebUI。

## Demo 使用流程

### 公共知识库主线

1. 启动后端和前端。
2. 打开 `http://127.0.0.1:5173`。
3. 点击“一键导入样例”。
4. 进入“公共知识库”，查看《微积分 II》第 5 章 `5.1-5.2` 的知识点目录。
5. 打开知识点详情，查看讲解、定义、定理、例题和习题。
6. 在知识点详情页提交课堂笔记。
7. 进入“笔记审核”，通过该笔记。
8. 返回知识点详情页，查看已合并笔记。
9. 在“当前知识点问答”中提问，查看基于当前知识点内容生成的回答。

### 个人学习空间主线

1. 进入“个人学习空间”。
2. 上传 `.md` / `.markdown` / `.txt` 文件，或点击“用样例创建个人空间”。
3. 查看自动生成的个人目录和知识点详情。
4. 使用当前个人资料问答。
5. 标记知识点状态：未开始、学习中、已掌握、疑难点。
6. 查看个人学习进度统计。
7. 点击“申请贡献到公共库”，提交整段个人知识点进入审核队列。
8. 在“审核中心”通过贡献后，回到公共知识库查看新增社区内容。

### 资料处理说明

当前资料处理链路设计为：

```text
PDF / 文档
→ mineru_tools 解析为 Markdown
→ text_archiver 清洗断行、格式和标题层级
→ owlsome_core 规范化为 Obsidian-compatible Markdown
→ learning_platform 切分知识点并生成学习空间
```

第一版 demo 为了保证现场稳定，优先使用已有 MinerU Markdown 样例和 Markdown 上传；真实 PDF 上传解析会在后续阶段接入。

## 可选 LLM 配置

不配置 API Key 也能完整离线演示。若需要模型增强问答，可在后端运行环境中设置：

```powershell
$env:LLM_API_KEY="你的 DeepSeek Key"
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_MODEL="deepseek-v4-flash"
```

旧的 `OPENROUTER_API_KEY`、`OPENROUTER_BASE_URL`、`OPENROUTER_MODEL` 和 `MODEL_NAME` 仍兼容；新配置优先级更高。

然后启动后端：

```powershell
cd D:\Projects\EL\learning_platform\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 功能规划

### Stage 1：本地 MVP 与比赛展示闭环

- 本地前后端稳定启动。
- 样例知识库导入。
- 笔记提交、审核与合并。
- 当前知识点问答。

### Stage 2：资料处理链路与 Obsidian-compatible 知识格式

- PDF 转 Markdown 链路标准化。
- Markdown 清洗与排版增强。
- `text_archiver` 已支持抽样生成本书规范、分段并发处理和 report 输出。
- Obsidian callout、wikilink、高亮和 LaTeX 渲染稳定。

### Stage 3：私人内容的可选贡献与审核闭环

- 已建立私人空间、贡献空间和公共知识库的数据边界。
- 用户资料默认 private。
- 个人知识点可主动申请贡献。
- 贡献进入审核队列，经预审和人工审核后合并进公共知识库。
- 首页可展示待审核贡献、已合并贡献和社区内容统计。

### Stage 4：AI 学习交互增强

- 题目与知识点挂钩。
- 关联例题、习题、错题和知识点问答。
- 学习进度与个性化建议。
- 练习与错题闭环。

### Stage 5：开源协作、部署与工程化

- Docker / Docker Compose 一键部署。
- SQLite demo 数据迁移到 PostgreSQL 或等价生产数据库。
- 贡献指南、Issue 模板、PR 模板。
- 展示脚本和答辩材料。

## 用户角色与权限

登录系统计划接入南哪小帮手回调，由专人负责实现；当前文档只定义业务权限。

| 角色 | 权限范围 | 说明 |
|---|---|---|
| 游客 | 浏览公开知识库和演示样例 | 不可上传私人资料，不可提交贡献 |
| 学习者 | 上传私人资料、创建个人学习空间、问答、记录进度、申请贡献 | 默认角色，上传内容默认 private |
| 贡献者 | 在学习者权限基础上，提交笔记、题解、讲解、错题等贡献 | 贡献进入审核队列，不直接进入公共库 |
| 审核者 | 查看待审核贡献、修改匹配知识点、通过、驳回、要求修改 | 可由项目维护者、助教或指定同学担任 |
| 管理员 | 管理课程、公共知识库、审核者权限和系统配置 | 负责公共知识库质量和系统运行 |

## 时间线与里程碑

以下时间线以 8 周开发周期为参考，可根据实际比赛截止日期压缩或扩展。

| 周期 | Stage | 关键交付物 | 里程碑验收 |
|---|---|---|---|
| Week 1 | Stage 1 | 本地 MVP 启动、样例知识库导入、基础 README | 前后端可启动，样例导入成功 |
| Week 2 | Stage 1 | 笔记提交、审核、合并、问答闭环 | 完成一次端到端演示 |
| Week 3 | Stage 2 | Obsidian-compatible 输出与渲染稳定 | callout、wikilink、LaTeX 正常展示 |
| Week 4 | Stage 2 | text_archiver 抽样规范与分段并发原型 | 完成 2 万字以上样例并行清洗测试 |
| Week 5 | Stage 3 | 私人空间、贡献空间、公共库边界和数据模型 | 上传资料默认 private，贡献可进入 pending |
| Week 6 | Stage 3 | 贡献审核页、预审、合并到公共库 | 完成私人内容到公共库的审核闭环 |
| Week 7 | Stage 4 | 题目-知识点挂钩原型、错题状态回流 | 完成题目双向关联和错题反馈演示 |
| Week 8 | Stage 5 | 文档、部署说明、展示脚本、答辩材料 | 队友按文档可复现演示流程 |

## 文档索引

- [项目企划书](docs/owlsome_learning_project_proposal.md)
- [PDF 转 Markdown 技术实现](docs/pdf_to_markdown_implementation.md)
- [Markdown 清洗技术实现](docs/markdown_cleanup_implementation.md)
- [Obsidian 兼容说明](docs/obsidian_compatibility.md)
- [版本控制策略](docs/version_control_strategy.md)
- [实现概览](docs/implementation_overview.md)

## 开发验证命令

后端编译检查：

```powershell
cd D:\Projects\EL
python -m compileall D:\Projects\EL\learning_platform\backend\app
```

前端生产构建：

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm run build
```

Git 状态检查：

```powershell
cd D:\Projects\EL
git status --short --branch
```

## 当前重点

近期优先推进：

1. 完善贡献内容的编辑与二次修改流程。
2. 为贡献审核增加更细的目标知识点人工改选能力。
3. 接入 embedding / rerank，提高贡献匹配准确率。
4. 用真实长教材样例压测 `text_archiver --parallel`，记录速率限制和加速比。
5. 准备题目-知识点挂钩的人工标注样例集。
