# AI 交互式数学学习平台 Demo

第一版 demo 主线是“公共教材知识库构建 + 笔记审核合并”。它复用现有 `mineru_tools` 的 Markdown 输出，不重写 PDF 解析工具。

## 启动后端

```powershell
cd D:\Projects\EL\learning_platform\backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 启动前端

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5173`，点击“一键导入样例”即可构建第 5 章 5.1-5.2 知识库。导入源优先级为：

1. `D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_formatted.md`
2. `D:\Projects\EL\learning_platform\sample_data\calculus_ii_chapter5_mineru.md`
3. `D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full.md`

也就是说，本地存在完整 `text_archiver` 清洗结果时，demo 会优先使用清洗后的 Obsidian-compatible Markdown； fresh clone 或离线演示仍可回退到仓库内置样例。

管理员模式的“系统概览”还提供“微积分 II 全书导入”入口：

- `先做 dry-run`：只切分清洗版教材并生成报告，不写入 SQLite。
- `导入清洗版全书`：重建同名课程并导入第 5–10 章公共资源库。

该入口调用后端 `POST /api/import/calculus-full`，普通学习者模式不可见。导入完成后公共资源库会按章节树展示全书结构。

## 前端构建时 dist 被占用

如果执行 `npm run build` 时出现类似错误：

```text
EPERM: operation not permitted, unlink 'D:\Projects\EL\learning_platform\frontend\dist\assets\index-xxx.js'
```

说明旧的 `dist` 产物正在被 Windows 进程占用。常见处理方式：

1. 关闭正在运行的 `npm run dev`、`vite preview`、静态文件服务器或打开了 `dist` 文件的编辑器预览。
2. 关闭正在查看旧构建页面的浏览器标签页。
3. 在任务管理器中结束残留的 `node.exe` 进程，或在 PowerShell 中查看并结束：

```powershell
Get-Process node
Stop-Process -Name node -Force
```

4. 手动删除旧构建目录后重试：

```powershell
Remove-Item -LiteralPath D:\Projects\EL\learning_platform\frontend\dist -Recurse -Force
cd D:\Projects\EL\learning_platform\frontend
npm run build
```

如果只是想确认代码能否打包，可临时输出到另一个目录：

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm run build -- --outDir dist_check
Remove-Item -LiteralPath D:\Projects\EL\learning_platform\frontend\dist_check -Recurse -Force
```

## 准备演示数据

比赛展示前可以用 seed 工具一键准备稳定数据。该命令会备份并重建本地 SQLite 数据库，不会提交数据库、备份文件或 `.env`：

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\seed_demo.py --all
```

执行后前端应能看到：

- 公共知识库已有 8 个知识点。
- 个人学习空间已有样例空间。
- 审核中心有 1 条待审核贡献。
- 公共知识点详情页已有 1 条“社区贡献”。
- 首页统计卡片显示 pending / approved / community 内容。

## 比赛前推荐准备命令

如果需要展示完整《微积分 II》公共资源库，建议按下面顺序做一次结构预检、内容 QA 和真实导入：

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\import_calculus_full.py --dry-run --report D:\Projects\EL\docs\test_records\calculus_full_import_report.md
python scripts\content_quality_audit.py --report D:\Projects\EL\docs\test_records\calculus_content_quality_audit.md
python scripts\import_calculus_full.py --import --reset-course
```

对应演示材料：

- `D:\Projects\EL\docs\demo\demo_paths.md`
- `D:\Projects\EL\docs\demo\competition_demo_script_5min.md`

## 微积分 II 全书结构化导入

完整清洗版教材可先用纯规则脚本做 dry-run，不调用 LLM、不写数据库，只生成结构化验收报告：

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\import_calculus_full.py --dry-run --report D:\Projects\EL\docs\test_records\calculus_full_import_report.md
```

确认报告中的章节、知识点和内容单元统计可接受后，再执行真实导入：

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\import_calculus_full.py --import --reset-course
```

也可以通过 API 验证：

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/import/calculus-full -ContentType "application/json" -Body '{"dry_run":true,"reset_course":false,"write_report":true}'
```

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/import/calculus-full -ContentType "application/json" -Body '{"dry_run":false,"reset_course":true,"write_report":true}'
```

第一版规则导入会优先读取本地 `merged_full_formatted.md`，识别章、节/小节、定义、定理、例题和习题，并生成 Markdown 验收报告。当前 dry-run 在清洗版《微积分 II》中识别出 6 章、76 个知识点和 638 个内容单元。它不做数学内容审校，也不自动判定题目与知识点的高精度关联。

公共资源库页面支持按章节树浏览完整第 5–10 章，也支持搜索章节标题、知识点编号、标题、摘要和标签。知识点详情页顶部会显示面包屑，例如：

```text
数学 / 微积分 II（第四版） / 第 5 章 多元函数微分学 / 5.1.1 点集基本知识
```

内容 QA 报告会标记过长、过短、公式符号疑似不平衡或 marker 识别不足的知识点。二次切分只在已有定义/定理/例题/习题等稳定边界上进行；无法可靠切分的内容会进入人工复核队列。

## 个人学习空间

前端“个人学习空间”页面支持两种稳定演示方式：

- 上传 `.md` / `.markdown` / `.txt` 文件，系统会自动切分为个人知识点。
- 点击“用样例创建个人空间”，复用已有 MinerU Markdown 快速生成个人学习空间。

第一版 PDF 上传作为占位入口展示，后续接入链路为 `mineru_tools → text_archiver → learning_platform`。

## Obsidian 兼容

系统现在优先使用 Obsidian-compatible Markdown：

- 支持 YAML frontmatter 作为资料元数据。
- 保留 `[[双链]]`、`> [!note]` callout、`==高亮==`、任务列表、LaTeX 公式和图片链接。
- MinerU 输出和 text_archiver 清洗结果都会尽量规范化为 Obsidian 友好的 Markdown。

## 可选 LLM 增强

不配置 API Key 也能完整离线演示。若需要模型增强问答，可在后端运行环境中设置：

```powershell
$env:LLM_API_KEY="你的 DeepSeek Key"
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_MODEL="deepseek-v4-flash"
```

旧的 `OPENROUTER_*` 与 `MODEL_NAME` 变量仍兼容；当前建议先用 DeepSeek 官方 OpenAI-compatible API，后续本地或内网模型部署好后只替换 `LLM_*`。

## 可选 BGE 检索增强

当前默认关闭，不影响现有规则匹配和离线 demo。上级部署 `BAAI/bge-m3` 与 `BAAI/bge-reranker-v2-m3` 后，可复制 `D:\Projects\EL\learning_platform\backend\.env.example` 为本地 `.env` 并填写服务地址：

```env
RETRIEVAL_PROVIDER=off
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_BASE_URL=
RERANKER_API_KEY=
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
```

本地或内网部署通常可以不填 API Key；如果服务端要求鉴权，再填对应 key。验证命令：

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\retrieval_probe.py --query "二重极限为什么不能只看一条路径" --top-k 8 --rerank-top-k 3 --ensure-sample
```

当 `RETRIEVAL_PROVIDER=off`、配置缺失或检索服务不可用时，系统会自动回退到当前关键词规则匹配。
