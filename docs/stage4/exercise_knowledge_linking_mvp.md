# Stage 4: 题目-知识点挂钩 MVP

## 目标闭环

```
题目录入
→ 系统推荐关联知识点 Top-3
→ 管理员人工确认绑定
→ 知识点详情页展示关联练习
→ 学习者提交做题结果
→ 系统记录练习尝试
```

本轮不是完整题库系统，而是跑通最小闭环。

## 数据表

### exercises

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 |
| title | TEXT | 题目标题 |
| stem | TEXT | 题干 |
| answer | TEXT | 答案/解析提示 |
| analysis | TEXT | 解析说明 |
| exercise_type | TEXT | practice / homework / exam |
| difficulty | INTEGER | 1-5 |
| source | TEXT | 来源标注 |
| status | TEXT | draft / linked / archived |
| created_at | TEXT | 创建时间 |

### exercise_knowledge_links

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 |
| exercise_id | INTEGER FK | → exercises.id |
| knowledge_point_id | INTEGER FK | → knowledge_points.id |
| confidence | REAL | 置信度 0-1 |
| reason | TEXT | 匹配理由 |
| confirmed_by | TEXT | 确认人标识 |
| created_at | TEXT | 创建时间 |

UNIQUE(exercise_id, knowledge_point_id)

### exercise_attempts

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | 自增 |
| exercise_id | INTEGER FK | → exercises.id |
| knowledge_point_id | INTEGER FK | → knowledge_points.id |
| result | TEXT | correct / wrong / unsure |
| note | TEXT | 备注 |
| created_at | TEXT | 创建时间 |

## API

```text
POST /api/exercises                       创建题目（默认 status=draft）
GET  /api/exercises                       列出所有题目
GET  /api/exercises/{id}                  查看单个题目
POST /api/exercises/recommend             推荐 Top-K 知识点
POST /api/exercises/{id}/link             确认绑定知识点
GET  /api/knowledge-points/{id}/exercises 查看已绑定题目
POST /api/exercises/{id}/attempts         提交练习结果
```

扩展统计字段（`GET /api/stats`）：

- `exercises` — 题目总数
- `linked_exercises` — 已绑定题目数
- `exercise_attempts` — 练习尝试数

## 匹配策略

1. 优先尝试 `app.services.retrieval`（BGE embedding/reranker），provider=off 或服务不可用时自动 fallback。
2. 关键词规则 fallback：对题目文本和知识点文本做中文分词，计算重叠 token 得分，返回 Top-K。
3. 推荐结果包含 `code`、`title`、`score`、`reason`。
4. 人工确认绑定后写入 `exercise_knowledge_links`，更新 `exercises.status = 'linked'`。
5. 推荐只是建议，不自动绑定；人工确认永远优先。

## 人工确认逻辑

- 管理员在"题目管理"页面查看 Top-3 推荐，手动点击"确认绑定"。
- 绑定写入 `exercise_knowledge_links` 表，confidence 默认 1.0。
- 同一题目可绑定多个知识点；同一知识点可关联多道题目。
- UNIQUE 约束防止重复绑定。

## 前端入口

### 题目管理（仅管理员可见）

导航：管理员模式 → 题目管理

功能：
- 创建题目（标题、题干、答案、解析、难度）
- 查看题目列表
- 为题目推荐知识点（Top-3）
- 确认绑定

### 知识点详情页（所有用户可见）

公共资源库 → 选择知识点 → 详情页底部"关联练习"区域：
- 显示该知识点已绑定的题目
- 提供"做对/做错/不确定"按钮
- 折叠显示答案与解析

### 系统概览统计（仅管理员可见）

新增统计卡片：题目数、已绑定题目数、练习尝试数

## 验证命令

```powershell
cd D:\Projects\EL\learning_platform\backend
python -m compileall D:\Projects\EL\learning_platform\backend\app D:\Projects\EL\learning_platform\backend\scripts
python scripts\smoke_test.py
```

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm run build
```

## 当前限制

- 不做完整题库系统（无批量导入、无分类管理）。
- 不做自动判分（只有手动提交 correct/wrong/unsure）。
- 不做错题本完整系统（只有 attempt 记录，无个性化重练）。
- 不要求 BGE 服务已部署（关键词 fallback 可靠）。
- 不要求 LLM Key。
- 不做学生与题目之间的个性化推荐。
