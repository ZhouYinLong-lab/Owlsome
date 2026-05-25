这个项目本身不做 PDF 解析，它是 MinerU (https://mineru.net) 云服务的 Python 客户端。PDF → Markdown 的 OCR/解析工作在
  MinerU 服务端完成，本项目负责：提交文件、轮询进度、下载结果。

  ---
  整体流程

  PDF 文件 → 上传到 MinerU 云 → 服务端 AI 解析 → 下载 ZIP/Markdown 结果

  项目提供了两种 API 模式：

  1. 精准解析 API（MinerUClient）

  入口：mineru_client/client.py:207

  - 需要 API Token（在 mineru.net 申请）
  - 支持大文件（≤200页、≤200MB）
  - 提交任务 → 轮询等待 → 下载 ZIP 压缩包 → 解压后读取其中的 full.md
  - 核心方法是 parse_url()（行462），链式调用三个步骤：
    a. submit_task()（行261）— POST 提交文件 URL 到 /api/v4/extract/task
    b. wait_for_task()（行368）— 每 2 秒轮询 /api/v4/extract/task/{task_id}，直到 state == "done"
    c. download_result()（行419）— 下载 full_zip_url，用 zipfile 解压，调用 utils.py:51 的 read_markdown() 读取 .md 文件

  2. 轻量解析 API（AgentClient）

  入口：mineru_client/client.py:826

  - 免 Token，受 IP 限频
  - 限制严格：文件 ≤10MB、≤20 页
  - 流程类似：parse_file()（行903）→ 获取预签名上传 URL → PUT 上传 → 轮询 → 直接从 Markdown CDN 链接下载内容


  PDF 文件 → 上传到 MinerU 云 → 服务端 AI 解析 → 下载 ZIP/Markdown 结果

  项目提供了两种 API 模式：

  1. 精准解析 API（MinerUClient）

  入口：mineru_client/client.py:207

  - 需要 API Token（在 mineru.net 申请）
  - 支持大文件（≤200页、≤200MB）
  - 提交任务 → 轮询等待 → 下载 ZIP 压缩包 → 解压后读取其中的 full.md
  - 核心方法是 parse_url()（行462），链式调用三个步骤：
    a. submit_task()（行261）— POST 提交文件 URL 到 /api/v4/extract/task
    b. wait_for_task()（行368）— 每 2 秒轮询 /api/v4/extract/task/{task_id}，直到 state == "done"
    c. download_result()（行419）— 下载 full_zip_url，用 zipfile 解压，调用 utils.py:51 的 read_markdown() 读取 .md 文件

  2. 轻量解析 API（AgentClient）

  入口：mineru_client/client.py:826

  - 免 Token，受 IP 限频
  - 限制严格：文件 ≤10MB、≤20 页
  - 流程类似：parse_file()（行903）→ 获取预签名上传 URL → PUT 上传 → 轮询 → 直接从 Markdown CDN 链接下载内容

  3. 大 PDF 拆分（PDFSplitter）

  入口：mineru_client/pdf_splitter.py:31

  - 当 PDF 超过 200 页时，parse_large_pdf()（client.py:509）自动触发
  - 用 pypdf 将 PDF 按每 200 页切分为多个子文件
  - 通过批量上传 API（/api/v4/file-urls/batch）并发提交各分块
  - 使用 ThreadPoolExecutor 并发处理（默认 5 线程），最后调用 merge_markdown_results()（pdf_splitter.py:139）将各块的 Markdown 拼接合并，块之间用 --- 分隔

  4. Web 界面（webui/）

  FastAPI 应用（webui/app.py），提供：
  - 网页上传 PDF 或输入 URL
  - 实时 SSE 进度推送
  - 任务历史记录（SQLite）

  ---
  总结

  一句话：本地负责文件上传和结果下载，真正的 PDF→MD 转换由 MinerU 云端 AI 模型（vlm/pipeline）完成，本项目是这套云 API 的 Python 封装 + Web 操作界面。