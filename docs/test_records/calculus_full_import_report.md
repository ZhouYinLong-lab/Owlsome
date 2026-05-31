# 微积分 II 全书结构化导入报告

- 生成时间：2026-05-31 10:45:35
- 输入文件：`D:\Projects\EL\mineru_tools\output\20260523_113153_Wei Ji Fen II(Di Si Ban ) - Zhang Yun Qing\merged_full_formatted.md`
- 导入数据库：否，dry-run 仅生成报告
- 执行入口：CLI 脚本
- 识别章节数：6
- 识别知识点数：76
- 识别内容单元数：638

## 内容单元统计

| 类型 | 数量 |
|---|---:|
| explanation | 186 |
| definition | 35 |
| theorem | 149 |
| example | 197 |
| exercise | 71 |

## 章节统计

| 章节 | 知识点 | 内容单元 | 警告 |
|---|---:|---:|---|
| 第 5 章 多元函数微分学 | 16 | 138 |  |
| 第 6 章 重积分 | 10 | 68 |  |
| 第 7 章 曲线积分·曲面积分·场论 | 18 | 101 |  |
| 第 8 章 无穷级数 | 17 | 181 |  |
| 第 9 章 傅里叶级数 | 3 | 17 |  |
| 第 10 章 常微分方程初步 | 12 | 133 |  |

## 抽样知识点

- `5.1.1` 点集基本知识：7 个单元；前几个类型：explanation, definition, definition, definition, definition, example
- `5.1.2` 多元函数的概念：2 个单元；前几个类型：definition, example
- `6.1.1` 二重积分的概念：4 个单元；前几个类型：explanation, definition, theorem, theorem
- `6.1.2` 二重积分的性质：5 个单元；前几个类型：explanation, theorem, theorem, theorem, exercise
- `7.1.1` 第一类曲线积分的概念与性质：3 个单元；前几个类型：explanation, definition, theorem
- `7.1.2` 第一类曲线积分的计算：10 个单元；前几个类型：explanation, theorem, explanation, explanation, example, example

## 异常提示

- 7.7.1 场的概念: 未识别到定义/定理/例题/习题 marker。
- 7.7.3 向量场的流量与散度: 未识别到定义/定理/例题/习题 marker。
- 7.7.4 向量场的环流量与旋度: 未识别到定义/定理/例题/习题 marker。

## 前端验收记录

- 管理员系统概览已提供全书 dry-run 与真实导入入口。
- 公共资源库左侧资源树应能按章节展示第 5–10 章。
- 章节可展开/收起，知识点详情页应继续显示教材来源与社区贡献标签。

## 验收建议

- 抽查每章首尾知识点，确认标题不是目录残留。
- 抽查公式密集段落，确认 LaTeX 未被破坏。
- 抽查例题和习题 marker，确认分类符合教材语义。
- 本报告只验证结构规则，不等价于数学内容审校。