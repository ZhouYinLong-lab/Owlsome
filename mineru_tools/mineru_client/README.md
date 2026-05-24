# MinerU API Client — Python 封装库

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

高效、可靠的 [MinerU](https://mineru.net/apiManage/docs) 文档解析 API Python 封装，内置**智能限流、指数退避重试、超大 PDF 自动拆分与结果合并**。

---

## 目录

- [特性](#特性)
- [安装](#安装)
- [快速开始](#快速开始)
- [两种 API 模式](#两种-api-模式)
- [核心功能](#核心功能)
  - [URL 解析](#1-url-解析)
  - [大 PDF 拆分解析](#2-大-pdf-拆分解析)
  - [批量解析](#3-批量解析)
  - [进度回调](#4-进度回调)
  - [Agent 轻量模式](#5-agent-轻量模式免登录)
- [API 参考](#api-参考)
- [高级配置](#高级配置)
- [错误处理](#错误处理)
- [注意事项](#注意事项)

---

## 特性

| 能力 | 说明 |
|------|------|
| 🔄 **双模式支持** | 精准解析 API（需 Token） + Agent 轻量 API（免登录） |
| 🚦 **智能限流** | 令牌桶 (Token Bucket) 速率控制，避免 429 |
| 🔁 **指数退避重试** | 自动识别 429/5xx，指数退避 + 随机抖动 |
| 📦 **大 PDF 拆分** | 超过 200 页自动拆分，并发处理，结果合并 |
| 🔀 **并发批量** | ThreadPoolExecutor 并发，可配置最大 workers |
| 📊 **进度回调** | 实时回调任务/块进度 |
| 🛡️ **类型安全** | 完整 dataclass 模型 + 类型注解 |
| 🧩 **轻量依赖** | 仅依赖 `requests` + `pypdf`，无重型框架 |

---

## 安装

```bash
pip install -e /path/to/mineru_client
```

或直接使用：

```bash
# 安装依赖
pip install requests pypdf

# 将 mineru_client/ 目录放到你的项目中即可
```

**依赖项：**
- `requests >= 2.28` — HTTP 请求
- `pypdf >= 3.0` — PDF 拆分
- （可选）`aiohttp >= 3.8` — 异步支持

---

## 快速开始

### 1. 申请 API Token

访问 https://mineru.net/apiManage/docs 注册并申请 Token。

### 2. 解析一个 PDF

```python
from mineru_client import MinerUClient

# 初始化客户端（填入你的 Token）
client = MinerUClient(token="your-api-token-here")

# 一行解析
result = client.parse_url("https://example.com/document.pdf")

print(f"任务 ID: {result.task_id}")
print(f"Markdown 长度: {len(result.markdown_content)} 字符")
print(f"结果目录: {result.local_output_dir}")

# 使用 Markdown 内容
print(result.markdown_content[:500])
```

### 3. 处理超大 PDF（自动拆分）

```python
# 500 页的 PDF，自动拆分为 3 块并发处理，最后合并
merge_result = client.parse_large_pdf(
    "large_document.pdf",       # 500 页大 PDF
    max_pages_per_chunk=200,    # 每块 200 页
    max_workers=3,              # 3 块并发
)

print(f"总页数: {merge_result.total_pages}")
print(f"成功块数: {merge_result.success_chunks}/{len(merge_result.chunks)}")
print(f"合并后 Markdown: {len(merge_result.merged_markdown)} 字符")
```

---

## 两种 API 模式

| 对比维度 | 🎯 精准解析 API (`MinerUClient`) | ⚡ Agent 轻量 API (`AgentClient`) |
|----------|-------------------------------|----------------------------------|
| Token | ✅ 必须 | ❌ 无需（IP 限频） |
| 文件大小 | ≤ 200MB | ≤ 10MB |
| 页数限制 | ≤ 200 页 | ≤ 20 页 |
| 批量支持 | ✅ (≤ 200 个) | ❌ 单文件 |
| 输出格式 | ZIP (MD + JSON + DOCX/HTML/LaTeX) | 仅 Markdown CDN 链接 |
| 模型版本 | pipeline / vlm / MinerU-HTML | 固定 pipeline |
| 调用方式 | 异步（提交 → 轮询） | 异步（提交 → 轮询） |

---

## 核心功能

### 1. URL 解析

```python
result = client.parse_url(
    file_url="https://example.com/paper.pdf",
    model_version="vlm",        # 推荐 vlm，精度最高
    enable_formula=True,        # 识别公式
    enable_table=True,          # 识别表格
    language="ch",              # 文档语言
    extra_formats=["docx"],     # 额外导出 docx
    page_ranges="1-10",         # 只解析前 10 页
)
```

### 2. 大 PDF 拆分解析

> 当 PDF **超过 200 页**时，API 会直接拒绝。`parse_large_pdf()` 自动拆分为 ≤200 页的多个子文件，**并发提交**处理，最后**合并**所有 Markdown。

```python
merge_result = client.parse_large_pdf(
    pdf_path="500_pages.pdf",
    max_pages_per_chunk=200,    # 每块最多页数
    max_workers=5,              # 最大并发数
    model_version="vlm",
    enable_formula=True,
)
# → 自动拆分为 3 块 → 3 个任务并发 → 合并为 merged_full.md
```

**工作流程：**
```
500_pages.pdf
    │
    ├── split ──→ chunk_0 (p1-200)  ──→ API Task 0 ──→ result_0.md
    ├── split ──→ chunk_1 (p201-400) ──→ API Task 1 ──→ result_1.md
    └── split ──→ chunk_2 (p401-500) ──→ API Task 2 ──→ result_2.md
                                                          │
                                                    merge_markdown()
                                                          ↓
                                                   merged_full.md
```

### 3. 批量解析

```python
urls = [
    "https://example.com/doc1.pdf",
    "https://example.com/doc2.pdf",
    "https://example.com/doc3.pdf",
]

batch = client.batch_parse_urls(
    file_urls=urls,
    max_workers=3,
    on_progress=lambda done, total: print(f"Progress: {done}/{total}"),
)

print(f"成功: {batch.success_count}, 失败: {batch.failed_count}")
print(f"成功率: {batch.success_rate:.1%}")
```

### 4. 进度回调

```python
def progress_callback(status):
    if status.progress:
        pct = status.progress.extracted_pages / status.progress.total_pages * 100
        print(f"\r→ {status.state.value}: {pct:.0f}%", end="")

result = client.parse_url(
    "https://example.com/doc.pdf",
    on_progress=progress_callback,
)
```

大 PDF 拆分进度：

```python
def chunk_callback(chunk_idx, total, status):
    print(f"[{chunk_idx+1}/{total}] {status.state.value}")

merge_result = client.parse_large_pdf(
    "large.pdf",
    on_chunk_progress=chunk_callback,
)
```

### 5. Agent 轻量模式（免登录）

```python
from mineru_client import AgentClient

agent = AgentClient()
result = agent.parse_url("https://example.com/small.pdf")

print(result.markdown_content)
# 限制：≤ 10MB / ≤ 20 页
```

---

## API 参考

### `MinerUClient`

```python
client = MinerUClient(
    token="...",                  # API Token（必须）
    base_url="https://mineru.net", # API 地址
    requests_per_second=3.0,      # 每秒请求数限制
    max_retries=5,                # 最大重试次数
    timeout=30,                   # HTTP 超时（秒）
    poll_interval=2.0,            # 轮询间隔（秒）
    task_timeout=600,             # 单任务超时（秒）
    output_dir="./mineru_output", # 默认输出目录
    auto_download=True,           # 自动下载结果
)
```

#### 主要方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `submit_task(file_url, ...)` | 提交解析任务 | `str` (task_id) |
| `get_task_status(task_id)` | 查询任务状态 | `TaskStatus` |
| `wait_for_task(task_id, ...)` | 轮询等待完成 | `TaskStatus` |
| `download_result(zip_url, ...)` | 下载解压结果 | `str` (目录路径) |
| `parse_url(file_url, ...)` | 一站式解析（提交+等待+下载） | `TaskResult` |
| `parse_large_pdf(pdf_path, ...)` | 大 PDF 拆分解析 | `MergeResult` |
| `batch_parse_urls(urls, ...)` | 批量解析 | `BatchResult` |

#### `submit_task()` 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_url` | `str` | (必填) | 文件 URL |
| `model_version` | `str` | `"vlm"` | 模型: `pipeline` / `vlm` / `MinerU-HTML` |
| `is_ocr` | `bool` | `False` | 是否启用 OCR |
| `enable_formula` | `bool` | `True` | 是否识别公式 |
| `enable_table` | `bool` | `True` | 是否识别表格 |
| `language` | `str` | `"ch"` | 文档语言 |
| `data_id` | `str` | `None` | 业务自定义标识 |
| `extra_formats` | `List[str]` | `None` | 额外格式: `["docx","html","latex"]` |
| `page_ranges` | `str` | `None` | 页码范围: `"2,4-6"` |
| `no_cache` | `bool` | `False` | 绕过缓存 |
| `cache_tolerance` | `int` | `900` | 缓存容忍秒数 |

### `TaskResult`

```python
@dataclass
class TaskResult:
    task_id: str                  # 任务 ID
    file_name: str                # 文件名
    full_zip_url: Optional[str]   # 结果 ZIP URL
    local_output_dir: Optional[str]  # 本地解压目录
    markdown_content: Optional[str]  # Markdown 文本内容
    metadata: Dict                # 元数据
    error: Optional[str]          # 错误信息
```

### `MergeResult`

```python
@dataclass
class MergeResult:
    original_file: str            # 原始 PDF 路径
    total_pages: int              # 总页数
    chunks: List[ChunkResult]     # 各块结果
    merged_markdown: Optional[str]  # 合并后 Markdown
    merged_output_dir: Optional[str] # 输出目录
    success_chunks: int           # 成功块数（属性）
    failed_chunks: int            # 失败块数（属性）
```

---

## 高级配置

### 自定义限流与重试

```python
from mineru_client.rate_limiter import RateLimiter

client = MinerUClient(
    token="...",
    requests_per_second=2.0,   # 保守：每秒 2 次
    max_retries=8,             # 最多重试 8 次
    task_timeout=1200,         # 大文件给 20 分钟
)
```

### 自定义 PDF 拆分参数

```python
merge_result = client.parse_large_pdf(
    "huge.pdf",
    max_pages_per_chunk=100,   # 每块 100 页（更保守）
    max_workers=2,             # 降低并发
)
```

### 手动控制流程

```python
# 手动提交
task_id = client.submit_task("https://example.com/doc.pdf")

# 手动轮询
status = client.get_task_status(task_id)
while not status.is_terminal:
    print(f"State: {status.state.value}")
    time.sleep(2)
    status = client.get_task_status(task_id)

# 手动下载
if status.full_zip_url:
    output = client.download_result(status.full_zip_url)
    md = read_markdown(output)
```

---

## 错误处理

```python
from mineru_client import (
    MinerUError, AuthenticationError, RateLimitError,
    TaskFailedError, TaskTimeoutError, FileTooLargeError,
)

try:
    result = client.parse_url("https://example.com/doc.pdf")
except AuthenticationError:
    print("Token 无效，请检查")
except RateLimitError as e:
    print(f"被限流，建议等待 {e.retry_after} 秒")
except TaskTimeoutError:
    print("任务超时，可增大 task_timeout")
except TaskFailedError as e:
    print(f"解析失败: {e.err_msg}")
except FileTooLargeError as e:
    print(f"文件过大: {e.file_size} > {e.max_size}")
except MinerUError as e:
    print(f"MinerU 错误: {e}")
```

---

## 注意事项

1. **Token 安全**：不要将 Token 硬编码在代码中，建议通过环境变量传递：
   ```python
   import os
   client = MinerUClient(token=os.environ["MINERU_TOKEN"])
   ```

2. **文件 URL 要求**：精准解析 API 需要文件可通过公网 URL 访问。如需上传本地文件，使用 `parse_large_pdf()` 内部已集成的批量上传机制。

3. **每日配额**：每个账号每天享有 **1000 页**最高优先级解析额度，超过后优先级降低。

4. **网络限制**：github、aws 等国外 URL 可能会请求超时，建议将文件上传到国内 CDN。

5. **并发控制**：大 PDF 拆分时 `max_workers` 不宜过大（推荐 3~5），避免触发限流。

6. **临时文件清理**：`parse_large_pdf()` 会自动清理拆分产生的临时 PDF 文件。

7. **Agent API 限制**：仅支持 ≤10MB / ≤20 页的 PDF，仅输出 Markdown，适合 AI Agent 轻量集成场景。

---

## 项目结构

```
mineru_client/
├── __init__.py          # 包入口，导出全部公开 API
├── client.py            # 核心客户端 (MinerUClient / AgentClient)
├── models.py            # 数据模型 (TaskResult, MergeResult, ...)
├── exceptions.py        # 异常体系
├── rate_limiter.py      # 令牌桶 + 指数退避重试
├── pdf_splitter.py      # PDF 拆分与 Markdown 合并
├── utils.py             # 工具函数 (ZIP 解压、MD 查找等)
├── requirements.txt     # 依赖列表
├── pyproject.toml       # 项目配置
└── README.md            # 本文件
```

---

## License

MIT License. 基于 [MinerU](https://github.com/opendatalab/MinerU) 开放 API 构建。
