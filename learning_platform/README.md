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
$env:OPENROUTER_API_KEY="你的 Key"
$env:OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
$env:MODEL_NAME="deepseek/deepseek-v4-flash:free"
```
