# 校园网服务器试部署准备测试记录

## 基本信息

| 项目 | 内容 |
|---|---|
| 日期 | 2026-05-31 |
| 基准 Commit Hash | `3c96fbb` (Finalize v0.1 product acceptance pass，本轮提交后以最新 `git log` 为准) |
| 环境 | Windows 11, Python 3.10+, Node.js 18+, npm 9+ |
| 服务器 | 未实际连接（本地验证） |

## 测试结果

### 后端编译

```powershell
cd D:\Projects\EL\learning_platform\backend
python -m compileall D:\Projects\EL\learning_platform\backend\app D:\Projects\EL\learning_platform\backend\scripts
```

✅ 无 SyntaxError，exit code 0。新增 `admin_auth.py` 和 `admin_guard_test.py` 均编译通过。

### Smoke Test（ADMIN_TOKEN 为空）

```
14/14 通过（不依赖 LLM Key）
```

✅ 本地 demo 兼容性确认：ADMIN_TOKEN 为空时所有现有功能不受影响。

### Admin Guard Test

```
21/21 通过
  - Un-guarded mode (ADMIN_TOKEN=""): 8/8 通过
  - Guarded mode (ADMIN_TOKEN="test-token"): 13/13 通过
    - 无 token 返回 403 ✅
    - 错误 token 返回 403 ✅
    - 正确 token 返回 200 ✅
    - 学习者接口不受影响 ✅
```

### 前端构建

```
npm run build — ✅ 成功
JS bundle: 794.88 kB (gzip: 246.52 kB)
```

### 安全检查

```
git status --short
```

- 无 `.env`（已通过 `.gitignore` 排除）
- 无 `*.db` / `*.db.bak`（已通过 `.gitignore` 排除）
- 无 `dist` / `dist_check` / `node_modules`
- 无 `mineru_tools/output`
- 无 `.claude` / `For claude.txt`

## 受保护的管理员端点（共 9 个）

| 端点 | 保护方式 |
|---|---|
| `POST /api/import/sample` | `dependencies=[Depends(require_admin_token)]` |
| `POST /api/import/calculus-full` | `dependencies=[Depends(require_admin_token)]` |
| `POST /api/notes/{id}/approve` | `dependencies=[Depends(require_admin_token)]` |
| `POST /api/notes/{id}/reject` | `dependencies=[Depends(require_admin_token)]` |
| `POST /api/contributions/{id}/approve` | `dependencies=[Depends(require_admin_token)]` |
| `POST /api/contributions/{id}/reject` | `dependencies=[Depends(require_admin_token)]` |
| `POST /api/contributions/{id}/request-revision` | `dependencies=[Depends(require_admin_token)]` |
| `POST /api/exercises` | `dependencies=[Depends(require_admin_token)]` |
| `POST /api/exercises/{id}/link` | `dependencies=[Depends(require_admin_token)]` |

## 前端改动

- `api.ts`: 新增 `readAdminToken()`, `writeAdminToken()`, `adminHeaders()`, `adminApi()`
- `App.tsx`: `importSample`, `importCalculusFull`, `approveNote`, `rejectNote`, `reviewContribution` 改用 `adminApi`
- `ExerciseManager.tsx`: `createExercise`, `link` 改用 `adminApi`
- `AppShell.tsx`: 首次切换到管理员模式时提示输入 token，保存到 `localStorage`
- `styles.css`: 新增 token 输入框样式

## 新增文件

| 文件 | 说明 |
|---|---|
| `app/admin_auth.py` | ADMIN_TOKEN 校验模块 |
| `scripts/admin_guard_test.py` | 管理员 token 保护测试（21 项） |
| `.env.server.example` | 后端服务器环境变量模板 |
| `frontend/.env.server.example` | 前端服务器构建配置模板 |
| `docs/deployment/campus_server_deployment_guide.md` | 校园网服务器部署完整指南 |

## 未实际连接服务器说明

本轮所有测试均在本地 Windows 环境完成。服务器实际部署需：

1. Clone 仓库到 Linux 服务器。
2. 复制 `.env.server.example` 为 `.env`，设置 `ADMIN_TOKEN`。
3. 按部署指南完成 Python venv 创建、依赖安装、seed 数据准备。
4. 启动后端（`--host 0.0.0.0`）和前端预览。
5. 在校园网内其他设备访问验证。

上述步骤需要实际服务器环境，不属于本地自动化测试范围。

## 追加核对

- `admin_auth.py` 会主动加载项目根目录 `.env` 与 `learning_platform/backend/.env`，并以后端 `.env` 为准。
- 服务器按部署指南复制 `.env.server.example` 为 `.env` 后，`ADMIN_TOKEN` 不需要额外 shell export 即可生效。
