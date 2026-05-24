# Owlsome Learning

Owlsome Learning 是猫头鹰组面向 EL 大赛交互组开发的 AI 交互式数学学习平台。项目目标是把静态教材、PDF、讲义和笔记转换成可拆解、可审核、可问答、可跟踪进度的学习空间。

## 当前 Demo

当前仓库已经包含第一版可展示 demo：

- 公共教材知识库：从 MinerU Markdown 样例导入《微积分 II》第 5 章 5.1-5.2。
- 知识点结构化：自动拆分知识点、定义、定理、例题、习题。
- 笔记审核合并：学生笔记先进入审核区，审核通过后合并到知识点。
- 个人学习空间：支持上传 Markdown / TXT，生成个人知识点目录、详情、问答和进度。
- 离线可演示：没有 LLM API Key 时也能完整跑通；配置 OpenRouter 后可增强问答。

## 项目结构

```text
Owlsome
├─ learning_platform      # 当前主 Demo：FastAPI + React + SQLite
├─ mineru_tools           # PDF / 文档解析工具，负责 PDF -> Markdown
├─ text_archiver          # Markdown 清洗工具，负责断行、标题、格式修复
└─ 项目书_初稿.md          # 项目背景、路线图和 MVP 规划
```

## 快速启动

启动后端：

```powershell
cd learning_platform\backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动前端：

```powershell
cd learning_platform\frontend
npm install
npm run dev
```

访问：

```text
http://127.0.0.1:5173
```

## 演示建议

1. 进入“资料处理”，说明 `mineru_tools -> text_archiver -> learning_platform` 的链路。
2. 在“公共知识库”点击“一键导入样例”，展示教材被拆成知识点和内容单元。
3. 在知识点详情提交课堂笔记，进入“笔记审核”通过，再回到知识点查看合并结果。
4. 使用当前知识点问答，展示基于资料的交互学习。
5. 进入“个人学习空间”，用样例或上传 Markdown，展示个人目录、进度和问答。

## 可选 LLM 配置

不配置 API Key 也能完整离线演示。若需要模型增强问答，可设置：

```powershell
$env:OPENROUTER_API_KEY="你的 Key"
$env:OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
$env:MODEL_NAME="deepseek/deepseek-v4-flash:free"
```

## 当前定位

这是比赛 demo 的起步仓库。后续会继续补齐：

- PDF 实时上传解析到个人空间
- LLM 精细结构化切分
- 练习生成、错题记录和推荐
- 更完整的项目文档、展示脚本和部署配置

