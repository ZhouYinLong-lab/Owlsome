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
