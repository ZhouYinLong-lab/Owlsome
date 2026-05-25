# text_archiver 并发清洗测试记录

本文档记录 `text_archiver` 抽样规范与分段并发清洗能力的阶段性测试。每次测试应保留输入文件、命令、环境、结果和后续动作，便于后续对比耗时、失败率和格式质量。

## 2026-05-25 完整《微积分 II》Dry Run

### 测试目标

验证完整 MinerU Markdown 能被 `text_archiver` 新增的 dry-run 流程正常识别，包括：

- 长文档读取。
- 自动分块数量统计。
- 自动 profile 抽样位置选择。
- 并发参数解析。
- report / profile / formatted 输出路径规划。
- dry-run 模式不调用 API、不写正式输出文件。

### 测试环境

| 项目 | 值 |
|---|---|
| 操作系统 | Windows / PowerShell |
| 项目目录 | `D:\Projects\EL` |
| 工具 | `text_archiver` |
| API Key | 未配置 `text_archiver\.env`，当前 shell 未检测到 `OPENROUTER_API_KEY` |
| 测试类型 | 无 API dry-run |

### 输入文件

```text
D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full.md
```

文件概况：

| 指标 | 值 |
|---|---:|
| 文件大小 | 约 743 KB |
| 文本字符数 | 589,209 |
| 行数 | 10,590 |
| 内容 | 《微积分 II（第四版）》完整 MinerU Markdown |

### 执行命令

```powershell
$p = 'D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full.md'
python D:\Projects\EL\text_archiver\main.py $p --dry-run --parallel 4 --auto-profile --profile-samples 5 --report
```

### 关键输出

```text
输入文件: D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full.md (589,209 字符)
模型: deepseek/deepseek-v4-flash:free
API: https://openrouter.ai/api/v1
分块: 159 块 (每块 ~4,000 字, 重叠: 段)

[Dry Run] 不调用 API，不写 formatted 输出。
输出: D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_formatted.md
报告: D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_formatted.md.report.json
并发: 4
自动规范: 是
规范输出: D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_profile.md
抽样分块: 1, 37, 80, 154, 159
```

### 验收结果

| 验收项 | 结果 |
|---|---|
| 能读取完整教材 Markdown | 通过 |
| 能按默认参数完成分块规划 | 通过，159 块 |
| 能选择 profile 抽样块 | 通过，选择 1、37、80、154、159 |
| `--parallel 4` 参数解析正常 | 通过 |
| `--report` 路径规划正常 | 通过 |
| dry-run 不调用 API | 通过 |
| dry-run 不生成正式 formatted 文件 | 通过 |

### 结论

完整《微积分 II》样例可以作为 Stage 2.3 并发清洗压测输入。当前 dry-run 已验证文档规模、分块数量和抽样策略正常。

由于本地未配置 API Key，本次未进行真实 LLM 清洗、自动 profile 生成和并发耗时对比。

### 后续测试建议

配置 `OPENROUTER_API_KEY` 后，按以下顺序测试：

1. 小规模真实清洗，限制 `--chunk-size` 或选取教材片段，确认模型输出质量。
2. 完整教材串行基线：

```powershell
$p = 'D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full.md'
python D:\Projects\EL\text_archiver\main.py $p --parallel 1 --auto-profile --profile-samples 5 --report
```

3. 完整教材并发压测：

```powershell
$p = 'D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full.md'
python D:\Projects\EL\text_archiver\main.py $p --parallel 4 --auto-profile --profile-samples 5 --report
```

4. 若触发 API 速率限制，降低并发并增加退避：

```powershell
$p = 'D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full.md'
python D:\Projects\EL\text_archiver\main.py $p --parallel 2 --rate-limit-delay 5 --report
```

## 2026-05-25 sample_input 真实 API 单块测试

### 测试目标

验证配置 `text_archiver\.env` 后，小样本能否真实调用 OpenAI-compatible API，并生成 `formatted.md` 与 `report.json`。

### 输入文件

```text
D:\Projects\EL\text_archiver\sample_input.md
```

### 执行命令

第一次在默认沙箱环境执行：

```powershell
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --parallel 1 --report
```

结果为 `Connection error`，判断可能与沙箱网络限制有关。

第二次在允许网络访问的环境中执行：

```powershell
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --parallel 1 --report --no-resume
```

### 环境检查

未记录或暴露 API Key 原文，仅确认变量存在性：

| 变量 | 状态 |
|---|---|
| `OPENROUTER_API_KEY` | 已配置，长度 35 |
| `OPENROUTER_BASE_URL` | 已配置，值为 `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | 已配置，值为 `deepseek/deepseek-v4` |

### 关键输出

```text
输入文件: D:\Projects\EL\text_archiver\sample_input.md (239 字符)
模型: deepseek/deepseek-v4
API: https://openrouter.ai/api/v1
分块: 1 块 (每块 ~4,000 字, 重叠: 段)

[重试] 分块 1 失败 (尝试 1/3): Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}}
[重试] 分块 1 失败 (尝试 2/3): Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}}
[错误] 分块 1 最终失败: Error code: 401 - {'error': {'message': 'Missing Authentication header', 'code': 401}}

输出文件: D:\Projects\EL\text_archiver\sample_input_formatted.md
处理报告已保存至: D:\Projects\EL\text_archiver\sample_input_formatted.md.report.json
```

### Report 摘要

| 字段 | 值 |
|---|---|
| `model` | `deepseek/deepseek-v4` |
| `parallel` | 1 |
| `total_chunks` | 1 |
| `done_chunks` | 0 |
| `failed_chunks` | 1 |
| `fallback_chunks` | `[0]` |
| `duration_seconds` | 9.267 |
| `fallback_to_original` | `true` |

### 验收结果

| 验收项 | 结果 |
|---|---|
| `.env` 能被 `main.py` 从项目根目录加载 | 通过 |
| 模型名能从 `OPENROUTER_MODEL` 读取 | 通过 |
| API 请求能发出到 OpenRouter | 通过，返回 401 |
| 失败后重试 3 次 | 通过 |
| 失败后保留原文 fallback | 通过 |
| report 能记录失败原因 | 通过 |
| 真实 LLM 清洗成功 | 未通过，401 `Missing Authentication header` |

### 初步判断

当前问题不在分块、并发、checkpoint 或 report 逻辑，而在 API 鉴权配置。建议下一步检查：

1. `OPENROUTER_API_KEY` 是否为 OpenRouter 平台生成的 key，而不是其他平台的 DeepSeek key。
2. 若使用 DeepSeek 官方 key，需要同步修改 `OPENROUTER_BASE_URL` 和模型名为对应平台的 OpenAI-compatible 配置。
3. 确认 `.env` 中 `OPENROUTER_API_KEY=` 后没有多余中文说明、占位符或不可见字符。

## 2026-05-25 sample_input DeepSeek 官方 API 成功测试

### 测试目标

将 provider 从 OpenRouter 切换为 DeepSeek 官方 OpenAI-compatible API 后，验证小样本真实清洗链路是否成功。

### 本地配置

未记录或暴露 API Key 原文，仅记录非敏感配置：

| 变量 | 值 |
|---|---|
| `OPENROUTER_BASE_URL` | `https://api.deepseek.com` |
| `OPENROUTER_MODEL` | `deepseek-v4-flash` |
| `OPENROUTER_API_KEY` | 已配置，长度 35 |

说明：当前代码仍沿用 `OPENROUTER_*` 变量名，但其含义已经是 OpenAI-compatible provider 配置，可指向 DeepSeek 官方 API。

### 执行命令

先验证配置读取：

```powershell
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --dry-run --parallel 1 --report
```

再执行真实 API 清洗：

```powershell
python D:\Projects\EL\text_archiver\main.py D:\Projects\EL\text_archiver\sample_input.md --parallel 1 --report --no-resume
```

### 关键输出

```text
输入文件: D:\Projects\EL\text_archiver\sample_input.md (239 字符)
模型: deepseek-v4-flash
API: https://api.deepseek.com
分块: 1 块 (每块 ~4,000 字, 重叠: 段)
云端格式化进度: 100%|██████████| 1/1 [00:07<00:00,  7.07s/块]

原始: 239 字符 → 格式化后: 468 字符 (+229)
输出文件: D:\Projects\EL\text_archiver\sample_input_formatted.md
处理报告已保存至: D:\Projects\EL\text_archiver\sample_input_formatted.md.report.json
```

### Report 摘要

| 字段 | 值 |
|---|---|
| `model` | `deepseek-v4-flash` |
| `parallel` | 1 |
| `total_chunks` | 1 |
| `done_chunks` | 1 |
| `failed_chunks` | 0 |
| `fallback_chunks` | `[]` |
| `duration_seconds` | 7.112 |
| `attempts` | 1 |
| `fallback_to_original` | `false` |

### 输出质量抽查

抽查 `sample_input_formatted.md`：

- 已生成 Obsidian-compatible YAML frontmatter。
- 标题层级从 `# / ## / ###` 正常输出。
- 无序列表与有序列表格式被修正。
- 中英文混排已有空格调整。
- 未出现 API 错误或 fallback 原文标记。

### 验收结果

| 验收项 | 结果 |
|---|---|
| DeepSeek 官方 API 配置读取 | 通过 |
| 真实 API 调用 | 通过 |
| 单块清洗成功 | 通过 |
| report 记录成功状态 | 通过 |
| 输出文件被 `.gitignore` 忽略 | 通过 |

### 结论

`text_archiver` 已能通过 DeepSeek 官方 API 完成小样本真实清洗。下一步可以进行完整《微积分 II》的小并发测试，建议先使用 `--parallel 2 --auto-profile --profile-samples 5 --report`，观察速率限制和单块平均耗时后再提高并发。

## 2026-05-25 完整《微积分 II》DeepSeek 并发清洗验收

### 测试目标

对完整《微积分 II（第四版）》MinerU Markdown 执行真实 LLM 清洗，验证 Stage 2.3 的完整闭环：

```text
完整 Markdown
→ 自动生成本书整理规范
→ parallel=2 分段并发清洗
→ checkpoint 记录
→ 顺序合并
→ Obsidian 后处理
→ formatted.md + report.json
```

### 输入与输出

| 项目 | 路径 / 值 |
|---|---|
| 输入 | `D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full.md` |
| 输出 | `D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_formatted.md` |
| 报告 | `D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_formatted.md.report.json` |
| 本书规范 | `D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_profile.md` |

### 执行命令

```powershell
$p = 'D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full.md'
python D:\Projects\EL\text_archiver\main.py $p --parallel 2 --auto-profile --profile-samples 5 --report
```

### 环境与配置

| 项目 | 值 |
|---|---|
| Provider | DeepSeek 官方 OpenAI-compatible API |
| Base URL | `https://api.deepseek.com` |
| Model | `deepseek-v4-flash` |
| Parallel | 2 |
| Chunk size | 4000 |
| Profile mode | `auto` |
| Profile size | 6,158 bytes |

### Report 摘要

| 字段 | 值 |
|---|---:|
| `total_chunks` | 159 |
| `done_chunks` | 159 |
| `failed_chunks` | 0 |
| `fallback_chunks` | 0 |
| `duration_seconds` | 2,158.487 |
| 总耗时 | 约 35 分 58 秒 |
| `average_chunk_seconds` | 62.009 |
| attempts | 159 个 chunk 均为 1 次成功 |
| 输出文件大小 | 745,832 bytes |
| report 大小 | 23,175 bytes |

最慢 chunk：

| chunk | seconds | attempts | fallback |
|---:|---:|---:|---|
| 91 | 141.17 | 1 | false |
| 86 | 129.48 | 1 | false |
| 72 | 120.62 | 1 | false |
| 119 | 118.65 | 1 | false |
| 53 | 114.27 | 1 | false |

### 输出抽查

头部抽查：

- 已生成 Obsidian-compatible YAML frontmatter。
- 标题、作者、封面图片引用均保留。
- 前言段落可读，未出现 API 错误文本。

尾部抽查：

- 文档尾部保留到第 10 章习题答案区域。
- 多个行内公式和块级公式仍以 LaTeX 形式存在。
- 未出现 chunk 顺序错乱或明显重复合并痕迹。

### 验收结果

| 验收项 | 结果 |
|---|---|
| 自动生成本书整理规范 | 通过 |
| 完整教材 159 块全部处理 | 通过 |
| 并发清洗 `parallel=2` | 通过 |
| chunk 输出按原顺序合并 | 通过 |
| 失败 chunk fallback 机制 | 未触发，报告为 0 |
| report 记录完整统计 | 通过 |
| Obsidian 后处理 | 通过 |
| 输出产物被 `.gitignore` 保护 | 通过，位于 ignored 的 `mineru_tools/output` |

### 结论

Stage 2.3 的核心能力已经通过完整教材真实测试：`text_archiver` 可以对 60 万字符量级的 MinerU Markdown 生成本书规范，并使用 DeepSeek 官方 API 进行稳定的分段并发清洗。此次测试没有 API 失败、没有 fallback、没有重试，说明 `parallel=2` 是当前较稳妥的默认压测配置。

后续优化方向：

1. 对比 `parallel=1` 和 `parallel=2` 的总耗时，量化并发加速比。
2. 抽样检查公式和表格密集区域，统计公式损坏率。
3. 优化 chunk 策略，减少 90 秒以上长尾 chunk。
4. 将 formatted 结果接入 `learning_platform` 个人空间或公共库导入流程。
