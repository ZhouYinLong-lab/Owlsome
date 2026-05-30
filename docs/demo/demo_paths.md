# Owlsome Learning 三条固定演示路径

本文用于比赛前彩排和队友交接。默认后端运行在 `http://127.0.0.1:8000`，前端运行在 `http://127.0.0.1:5173`。

## 演示前准备

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\seed_demo.py --all
```

如果需要展示《微积分 II》全书资源库：

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\import_calculus_full.py --import --reset-course
```

如果只想先检查结构质量，不写入数据库：

```powershell
cd D:\Projects\EL\learning_platform\backend
python scripts\import_calculus_full.py --dry-run --report D:\Projects\EL\docs\test_records\calculus_full_import_report.md
python scripts\content_quality_audit.py --report D:\Projects\EL\docs\test_records\calculus_content_quality_audit.md
```

## 路径一：教材导入到公共资源浏览

目标：证明平台能把教材资料变成可浏览、可检索、可问答的公共知识库。

1. 切换到“管理员模式”。
2. 进入“系统概览”。
3. 点击“微积分 II 全书导入”中的 `先做 dry-run`，说明这是结构化预检，不写数据库。
4. 点击 `导入清洗版全书`，说明导入源优先使用 `merged_full_formatted.md`，没有 LLM Key 也能跑。
5. 自动进入或手动进入“公共资源库”。
6. 展示左侧层级：`数学 / 微积分 II（第四版） / 第 5–10 章 / 知识点`。
7. 在搜索框输入 `隐函数`、`换元积分法` 或 `欧拉方程`，展示快速定位。
8. 点击一个知识点，展示面包屑、公式渲染、定义/定理/例题/习题单元和来源标签。

验收点：

- 章节树可展开/收起。
- 搜索后只显示匹配章节和知识点。
- 知识点详情顶部显示当前位置面包屑。
- 不依赖 BGE、本地模型或在线 LLM。

## 路径二：个人资料到私人学习空间和问答

目标：证明用户可以拥有不污染公共库的私人学习空间。

1. 切换到“学习者模式”。
2. 进入“个人学习空间”。
3. 点击“用样例创建个人空间”，或上传一个 Markdown 文件。
4. 在左侧选择个人空间，再选择个人知识点。
5. 展示右侧知识点内容、进度状态按钮。
6. 将状态从 `未开始` 改为 `学习中` 或 `已掌握`。
7. 在问答框输入：“这个知识点考试时最容易错在哪里？”并提交。
8. 说明离线模式会基于当前知识点内容生成模板化回答，有 LLM Key 时可增强。

验收点：

- 私人空间与公共资源库数据隔离。
- 上传 Markdown 或样例空间都能生成目录。
- 问答不要求 LLM Key。
- 学习进度可立即更新。

## 路径三：私人笔记贡献到公共库

目标：突出 Owlsome Learning 的差异点：私人内容可选贡献，审核后进入公共知识库。

1. 在“个人学习空间”选择一个个人知识点。
2. 点击“申请贡献到公共库”。
3. 保持默认标题或填写一个课堂补充标题，提交贡献。
4. 展示系统自动推荐公共知识点和匹配理由。
5. 切换到“管理员模式”。
6. 进入“审核中心”，查看待审核贡献。
7. 点击“通过”，说明审核动作会写入记录，并把贡献合并为公共内容单元。
8. 回到“公共资源库”，打开对应知识点，展示“社区贡献”标签和新增内容。

验收点：

- 普通学习者默认看不到审核中心。
- 未审核贡献不会直接污染公共资源库。
- 审核通过后公共知识点详情能看到社区贡献。
- 这条路径是项目相对普通教材解析工具的核心差异点。

## 讲解重点

- `mineru_tools` 负责 PDF/文档解析。
- `text_archiver` 负责 Markdown 清洗、Obsidian 兼容和并发处理。
- `learning_platform` 负责学习空间、公共资源库、审核闭环和交互展示。
- 当前 BGE 检索层默认关闭，未来用于“笔记/题目到知识点”的 Top-K 匹配增强。
