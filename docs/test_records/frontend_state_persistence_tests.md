# 前端状态持久化与个人空间搜索验收记录

- 验收对象：Owlsome Learning 前端演示连续性
- 存储方式：浏览器 `localStorage`
- 存储范围：tab、role、公共知识点、个人空间、个人知识点

## 实现说明

本轮只做前端本地状态恢复，不引入路由库、不写后端 session、不作为权限来源。

使用的 key：

| key | 含义 |
|---|---|
| `owlsome.role` | 当前演示角色 |
| `owlsome.tab` | 当前页面 tab |
| `owlsome.publicKnowledgePointId` | 最近公共知识点 |
| `owlsome.personalSpaceId` | 最近个人空间 |
| `owlsome.personalPointId` | 最近个人知识点 |

## 手动验收清单

- [ ] 切到管理员模式和“题目管理”，刷新后仍保持管理员模式和题目管理页。
- [ ] 切回学习者模式后，审核中心、系统概览、题目管理不显示。
- [ ] 在公共资源库选择一个知识点，刷新后仍选中该知识点。
- [ ] 在个人学习空间选择一个空间和知识点，刷新后仍恢复到该位置。
- [ ] 在个人学习空间搜索空间标题，可显示匹配空间。
- [ ] 在个人学习空间搜索知识点标题，可显示所属空间和匹配知识点。
- [ ] 清空搜索后恢复完整个人空间树。
- [ ] 在工作台点击薄弱知识点或最近错题后进入公共资源库，刷新后仍保持该知识点。
- [ ] 清空浏览器 localStorage 后刷新，默认回到学习者工作台且无报错。

## 自动验证

```powershell
cd D:\Projects\EL\learning_platform\backend
python -m compileall D:\Projects\EL\learning_platform\backend\app D:\Projects\EL\learning_platform\backend\scripts
python scripts\smoke_test.py
```

```powershell
cd D:\Projects\EL\learning_platform\frontend
npm run build
```

## 注意

- localStorage 状态可能因清缓存、换浏览器或无痕模式丢失。
- 管理员模式仍是前端演示隔离，不是安全权限。
- 若保存的知识点或个人空间已不存在，前端应静默回退到默认首项。
