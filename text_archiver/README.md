# text_archiver

`text_archiver` 是 Owlsome Learning 的 Markdown 清洗工具，用于修复 PDF 转 Markdown 后常见的断行、标题层级、列表、公式和 Obsidian 格式问题。

当前版本支持：

- 串行清洗，保持旧行为兼容。
- 分段并发清洗。
- 自动抽样生成“本书整理规范”。
- 使用已有整理规范清洗。
- 断点续传。
- diff 输出。
- Obsidian-compatible 后处理。
- JSON 处理报告。

## 安装依赖

```powershell
cd D:\Projects\EL\text_archiver
python -m pip install -r D:\Projects\EL\text_archiver\requirements.txt
```

复制环境变量：

```powershell
cd D:\Projects\EL\text_archiver
Copy-Item -Path D:\Projects\EL\text_archiver\.env.example -Destination D:\Projects\EL\text_archiver\.env
```

在 `.env` 中配置：

```text
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

当前推荐用 DeepSeek 官方 OpenAI-compatible API 临时承接清洗任务。未来切换本地或内网模型时，只需要替换 `LLM_BASE_URL`、`LLM_MODEL` 和按需填写 `LLM_API_KEY`。旧的 `OPENROUTER_*` 与 `MODEL_NAME` 变量仍兼容，已有 `.env` 不会失效。

## 无 API Key 验证

`--dry-run` 不调用 API，也不写 formatted 输出：

```powershell
cd D:\Projects\EL
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --dry-run --parallel 4 --auto-profile --profile-samples 3 --report
```

输出会显示：

- 输入文件
- 输出路径
- chunk 数量
- 并发数
- 是否自动生成规范
- 抽样 chunk 编号

## 串行清洗

```powershell
cd D:\Projects\EL\text_archiver
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --parallel 1 --obsidian --report
```

`--parallel 1` 保持旧版串行逻辑。

## 并发清洗

```powershell
cd D:\Projects\EL\text_archiver
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --parallel 4 --obsidian --report
```

说明：

- 多个 chunk 并发调用 OpenAI-compatible API。
- 输出时仍按原始 chunk 顺序合并。
- 每个 chunk 的状态会写入 checkpoint 和 report。
- 如果 API 有速率限制，降低 `--parallel` 或增大 `--rate-limit-delay`。

## 自动生成本书整理规范

```powershell
cd D:\Projects\EL\text_archiver
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --auto-profile --profile-samples 5 --parallel 4 --report
```

工具会从开头、中部、结尾和公式/标题密集片段抽样，生成：

```text
<输入文件>_profile.md
```

后续每个 chunk 的清洗 prompt 都会带上这份“本书整理规范”。

## 使用已有整理规范

```powershell
cd D:\Projects\EL\text_archiver
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --book-profile D:\Projects\EL\text_archiver\sample_input_profile.md --parallel 4 --report
```

适合先人工校正规范，再批量清洗整本书。

## Report 字段

启用 `--report` 后，会生成：

```text
<输出文件>.report.json
```

核心字段：

| 字段 | 说明 |
|---|---|
| `input` | 输入文件 |
| `output` | 输出文件 |
| `model` | 使用模型 |
| `parallel` | 并发数 |
| `chunk_size` | 分块大小 |
| `total_chunks` | 分块总数 |
| `profile_mode` | `none` / `auto` / `file` |
| `profile_output` | profile 文件路径 |
| `duration_seconds` | 总耗时 |
| `done_chunks` | 成功 chunk 数 |
| `failed_chunks` | 失败 chunk 数 |
| `fallback_chunks` | 降级为原文的 chunk |
| `average_chunk_seconds` | 平均 chunk 耗时 |
| `chunk_meta` | 每个 chunk 的状态、耗时、重试次数 |

## 断点续传

处理中断时会保留：

```text
<输入文件>.checkpoint.json
```

重新运行相同命令时，会复用已完成 chunk。

全部完成后 checkpoint 会自动删除。

## 常用参数

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `--parallel` | `1` | 并发 worker 数 |
| `--auto-profile` | 关闭 | 自动抽样生成本书规范 |
| `--profile-samples` | `5` | 抽样 chunk 数 |
| `--book-profile` | 空 | 使用已有本书规范 |
| `--profile-output` | `<输入>_profile.md` | 保存自动规范 |
| `--report` | 关闭 | 输出 JSON 报告 |
| `--rate-limit-delay` | `2` | API 失败后的基础退避秒数 |
| `--dry-run` | 关闭 | 只显示计划，不调用 API |
| `--diff` | 关闭 | 保存 unified diff |
| `--show-diff` | 关闭 | 终端显示 diff |
| `--no-obsidian` | 关闭 | 禁用 Obsidian 后处理 |

## 速率限制建议

如果 API 报 429、超时或频繁失败：

```powershell
python D:\Projects\EL\text_archiver\main.py input.md --parallel 2 --rate-limit-delay 5 --report
```

建议从 `--parallel 2` 开始，再逐步调高。
