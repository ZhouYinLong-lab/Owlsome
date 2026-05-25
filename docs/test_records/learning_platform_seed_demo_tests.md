# learning_platform Demo Seed 测试记录

## 2026-05-25 Seed 工具初始验证

### 目标

验证 `learning_platform/backend/scripts/seed_demo.py` 可以一键准备比赛演示数据：

```text
备份并重置 SQLite
→ 导入清洗版教材
→ 创建个人样例空间
→ 创建一条待审核贡献
→ 创建并审核通过一条社区贡献
```

### 计划命令

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\seed_demo.py --all
```

### 预期结果

| 指标 | 预期 |
|---|---:|
| 知识点数量 | 8 |
| 内容单元数量 | 大于 0 |
| 个人空间 ID | 非空 |
| pending 贡献数 | 至少 1 |
| approved 贡献数 | 至少 1 |
| 社区内容数 | 至少 1 |

### 验证说明

`--reset` 会备份当前数据库为 `learning_platform_YYYYMMDD_HHMMSS.db.bak`，再重建 `learning_platform.db`。数据库和备份文件位于 `learning_platform/backend/data`，已由 `.gitignore` 排除，不应提交到仓库。

### 实测结果

执行：

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\seed_demo.py --all
```

输出摘要：

```text
数据库路径: D:\Projects\EL\learning_platform\backend\data\learning_platform.db
备份路径: D:\Projects\EL\learning_platform\backend\data\learning_platform_20260525_213726.db.bak
导入源: D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_formatted.md
课程数: 1
知识点数量: 8
内容单元数量: 55
个人空间 ID: 1
pending 贡献数: 1
approved 贡献数: 1
社区内容数: 1
```

幂等性验证：

- 连续执行 `python scripts\seed_demo.py --all` 两次。
- 每次都会先备份并重建数据库。
- 最终统计稳定为 8 个知识点、1 条待审核贡献、1 条已通过贡献、1 条社区内容。

部分命令验证：

```powershell
python scripts\seed_demo.py --reset --import-sample
```

结果：

- 知识点数量为 8。
- 内容单元数量为 54。
- 个人空间、贡献、社区内容均为空，符合只导入样例的预期。

构建验证：

```powershell
python -m compileall D:\Projects\EL\learning_platform\backend\app
python -m compileall D:\Projects\EL\learning_platform\backend\scripts
cd D:\Projects\EL\learning_platform\frontend
npm run build
```

结果：均通过。Vite 仍有主 chunk 超过 500 KB 的提示，不影响本轮 seed 工具验收。
