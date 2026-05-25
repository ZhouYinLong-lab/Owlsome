# learning_platform 清洗版导入与 Stage 3 闭环测试记录

## 2026-05-25 清洗版教材导入验证

### 测试目标

验证 `learning_platform` 已优先使用 `text_archiver` 清洗后的完整教材：

```text
D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_formatted.md
```

同时确认清洗版 Markdown 可以被规则分段器稳定切出第 5 章 `5.1-5.2` 的知识点和内容单元。

### 验证方式

使用临时 SQLite 数据库验证，不改动当前演示数据库：

```powershell
cd D:\Projects\EL\learning_platform\backend
python -m compileall D:\Projects\EL\learning_platform\backend\app
```

脚本执行内容：

- 将 `app.db.DB_PATH` 临时指向 `%TEMP%\owlsome_clean_import_stage3_validation.db`。
- 执行 `init_db()`。
- 执行 `import_sample()`。
- 查询课程来源、知识点数量、内容单元数量和 Obsidian callout 数量。

### 结果

| 验收项 | 结果 |
|---|---|
| 实际导入源 | `merged_full_formatted.md` |
| 课程 source | `merged_full_formatted.md` |
| 知识点数量 | 8 |
| 内容单元数量 | 54 |
| 含 Obsidian callout 的内容单元 | 22 |
| content unit source | `text_archiver cleaned Markdown` |
| 编译检查 | 通过 |

识别出的知识点：

```text
5.1.1 点集基本知识
5.1.2 多元函数的概念
5.1.3 多元函数的极限
5.1.4 多元函数的连续性
5.2.1 偏导数
5.2.2 高阶偏导数
5.2.3 全微分
5.2.4 高阶微分*
```

### 相关修复

- 样例导入优先级调整为：
  1. `merged_full_formatted.md`
  2. 仓库内置章节样例
  3. 原始 MinerU `merged_full.md`
- 分段器支持 `## 5.1`、`### 5.1.1` 等清洗版标题。
- 分段器会跳过目录中的 `5.1/5.2`，寻找真正正文。
- 内容单元 source 会标记为 `text_archiver cleaned Markdown`。

## 2026-05-25 公共知识库展示修复

### 测试目标

确认清洗版教材进入公共知识库后，前端能更清楚地展示资料来源、Markdown 内容和审核贡献预览。

### 变更

- 公共知识点详情页中，来自清洗版教材的内容单元显示“清洗版教材”标签。
- 社区贡献内容继续显示“社区贡献”标签。
- 审核中心贡献预览改为 Markdown 渲染，支持公式、callout 和列表预览。
- 资料处理页文案更新为：
  - `mineru_tools` 产出完整 `merged_full.md`
  - `text_archiver` 产出完整 `merged_full_formatted.md`
  - `learning_platform` 优先读取清洗版结果

### 验证

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm run build
```

结果：构建通过。

备注：Vite 提示主 JS chunk 超过 500 KB，这是当前单文件 demo 结构和 KaTeX 资源导致的构建警告，不影响本轮验收。

## 2026-05-25 Stage 3 贡献审核闭环后端验证

### 测试目标

在临时数据库中验证：

```text
个人学习空间
→ 从个人知识点申请贡献
→ 进入 pending 队列
→ 审核通过合并到公共知识库
→ 驳回不污染公共知识库
```

### 结果

| 验收项 | 结果 |
|---|---|
| 创建个人样例空间 | 通过 |
| 从个人知识点创建贡献 | 通过，状态 `pending` |
| 自动推荐公共知识点 | 通过，推荐到 `5.1.1 点集基本知识` |
| pending 列表返回贡献 | 通过 |
| 审核通过 | 通过，状态 `approved` |
| 通过后写入公共 content_units | 通过，新增 `community_contribution:*` |
| 驳回贡献 | 通过，状态 `rejected` |
| 驳回后公共库不变 | 通过 |

### 结论

清洗版教材已能作为 `learning_platform` 的优先导入源，并且公共知识库展示与 Stage 3 私人贡献审核闭环均通过临时库验证。后续如果要让当前本地演示库切换为清洗版数据，需要先备份或清空：

```text
D:\Projects\EL\learning_platform\backend\data\learning_platform.db
```

然后重新点击“一键导入样例”。现有实现不会自动删除旧课程数据，这是为了避免误删演示中的笔记、贡献和问答记录。
