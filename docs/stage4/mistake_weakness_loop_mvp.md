# 错题与薄弱点闭环 MVP

## 目标闭环

在题目-知识点挂钩 MVP 基础上，实现第一版"错题与薄弱点闭环"：

```text
做题记录
→ 系统汇总 wrong / unsure
→ 生成错题列表和薄弱知识点
→ 学习者工作台展示
→ 用户点击回到知识点复习
→ 再次练习并更新记录
```

## API 说明

### GET /api/exercises/mistakes

返回最近 `wrong` / `unsure` 的练习记录。

参数：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| limit | int | 20 | 返回条数，最大 100 |

返回字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| attempt_id | int | 练习记录 ID |
| exercise_id | int | 题目 ID |
| knowledge_point_id | int \| null | 知识点 ID |
| result | string | "wrong" 或 "unsure" |
| note | string | 备注 |
| attempted_at | string | 提交时间 |
| exercise_title | string | 题目标题 |
| exercise_stem | string | 题目题干 |
| exercise_answer | string | 题目答案 |
| exercise_analysis | string | 题目解析 |
| knowledge_point_code | string \| null | 知识点编号 |
| knowledge_point_title | string \| null | 知识点标题 |

排序：`created_at DESC`

### GET /api/exercises/weak-points

按知识点统计 `wrong` / `unsure` 次数。

参数：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| limit | int | 10 | 返回条数，最大 100 |

返回字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| knowledge_point_id | int | 知识点 ID |
| code | string | 知识点编号 |
| title | string | 知识点标题 |
| wrong_count | int | 做错次数 |
| unsure_count | int | 不确定次数 |
| total_weak_attempts | int | 薄弱记录总数 |
| latest_attempt_at | string | 最近一次记录时间 |

排序：`total_weak_attempts DESC, latest_attempt_at DESC`

注意：

- `knowledge_point_id` 为空的记录不参与薄弱点统计。
- `correct` 结果不计入薄弱点。

### GET /api/stats 新增字段

| 字段 | 类型 | 说明 |
|---|---|---|
| mistake_attempts | int | `result = 'wrong'` 的数量 |
| unsure_attempts | int | `result = 'unsure'` 的数量 |
| weak_knowledge_points | int | 有 wrong/unsure 记录的知识点数量（去重） |

旧字段保持不变。

## 统计规则

1. **薄弱知识点识别**：按 `knowledge_point_id` 聚合 `result IN ('wrong', 'unsure')` 的记录，统计 `wrong_count`、`unsure_count`、`total_weak_attempts`。
2. **忽略空知识点**：`knowledge_point_id IS NULL` 的记录不计入薄弱点，但会出现在错题列表中。
3. **不计入 correct**：只有 `wrong` 和 `unsure` 参与薄弱点统计。
4. **排序**：按总薄弱次数降序，次数相同按最近记录时间降序。
5. **无个性化**：当前不区分用户，所有记录合并统计。

## 前端入口

### 学习者工作台（Dashboard）

在 `Dashboard.tsx` 中，学习者模式可见两个新区域：

1. **薄弱知识点列表**
   - 显示 `code`、`title`、`wrong_count`、`unsure_count`、`total_weak_attempts`
   - 点击后跳转到公共资源库并选中该知识点

2. **最近错题列表**
   - 显示题目标题/简短题干、result（做错/不确定）、对应知识点 code + title
   - 点击后跳转到公共资源库并选中知识点
   - 未绑定知识点的错题显示"未绑定知识点"提示

如果没有数据，显示："暂无错题记录，完成一次关联练习后这里会出现复习入口。"

### 公共知识点详情页（KnowledgeBase）

练习反馈优化：

- 提交成功后显示："已记录，工作台将更新薄弱点统计。"
- 提交失败时显示具体错误信息，不再静默失败。

### 系统概览（SystemOverview）

管理员模式下新增三张统计卡片：

- 错题记录（`mistake_attempts`）
- 不确定记录（`unsure_attempts`）
- 薄弱知识点（`weak_knowledge_points`）

## 验收路径

前置条件：已有至少一个绑定到知识点的练习。

1. 打开公共资源库。
2. 进入有练习的知识点。
3. 在关联练习中点击"做错"或"不确定"。
4. 回到学习者工作台。
5. 确认出现薄弱知识点和最近错题。
6. 点击薄弱知识点或错题。
7. 页面跳转/切换到公共资源库对应知识点。
8. 再点击"做对"。
9. 管理员系统概览中统计卡片更新：错题记录、不确定记录、薄弱知识点。

## 关键文件

| 文件 | 说明 |
|---|---|
| `app/services/exercises.py` | `list_mistake_exercises()`, `list_weak_knowledge_points()` |
| `app/main.py` | `GET /api/exercises/mistakes`, `GET /api/exercises/weak-points`, 扩展 `GET /api/stats` |
| `scripts/smoke_test.py` | 新增 3 项测试（mistakes, weak-points, stats 新字段） |
| `frontend/src/types.ts` | `MistakeExercise`, `WeakKnowledgePoint`, 扩展 `Stats` |
| `frontend/src/pages/Dashboard.tsx` | 薄弱点与错题区域 |
| `frontend/src/pages/KnowledgeBase.tsx` | 练习反馈优化 |
| `frontend/src/pages/SystemOverview.tsx` | 新增统计卡片 |
| `frontend/src/App.tsx` | `onOpenKnowledgePoint` 回调 |

## 当前限制

- **不做自动判分**：题目答案是否正确由用户自主判断（点击做对/做错/不确定）。
- **不做个性化推荐**：不根据薄弱点推荐新题目或学习路径。
- **不做完整错题本**：当前只展示最近错题列表，不支持错题收藏、分类、导出。
- **不区分用户**：所有记录合并统计，不按用户隔离。
- **不做长期学习曲线**：只统计当前薄弱点，不追踪历史变化趋势。

## Smoke Test 新增项

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\smoke_test.py
```

新增 3 项检查：

- `GET /api/exercises/mistakes` — 确认返回列表
- `GET /api/exercises/weak-points` — 确认返回列表
- `GET /api/stats (mistake/weak fields)` — 确认 `mistake_attempts`、`unsure_attempts`、`weak_knowledge_points` 均为整数

总检查项：14 项。
