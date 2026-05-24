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

访问 `http://127.0.0.1:5173`，点击“一键导入样例”即可从仓库内置样例 Markdown 构建第 5 章 5.1-5.2 知识库。本地如果存在完整 MinerU 输出，也可继续作为回退来源。

## 个人学习空间

前端“个人学习空间”页面支持两种稳定演示方式：

- 上传 `.md` / `.markdown` / `.txt` 文件，系统会自动切分为个人知识点。
- 点击“用样例创建个人空间”，复用已有 MinerU Markdown 快速生成个人学习空间。

第一版 PDF 上传作为占位入口展示，后续接入链路为 `mineru_tools → text_archiver → learning_platform`。

## 可选 LLM 增强

不配置 API Key 也能完整离线演示。若需要模型增强问答，可在后端运行环境中设置：

```powershell
$env:OPENROUTER_API_KEY="你的 Key"
$env:OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
$env:MODEL_NAME="deepseek/deepseek-v4-flash:free"
```
