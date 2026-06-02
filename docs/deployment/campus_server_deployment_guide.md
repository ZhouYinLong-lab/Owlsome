# Owlsome Learning 校园网服务器试部署指南

## 适用场景

- 校园网 / 内网服务器试部署，供队友访问测试。
- 不是正式公网生产部署（无 HTTPS、无真实登录、无 PostgreSQL）。

## 开发协作模式

```
本地开发 → git push GitHub → 服务器 git pull 验收
```

服务器**不是**主开发环境，只做 pull + 配置 + 启动 + 验收。
如果在服务器上跑 Claude Code，只做部署诊断和小修。

## 推荐一键启动

当前推荐使用 systemd 一键脚本托管前后端：

```bash
cd /data/workspace/projects/Owlsome
git pull
sudo bash deployment/systemd/install_owlsome_services.sh
```

脚本会自动安装依赖、构建前端、生成 systemd service、设置开机自启并验证服务。默认端口：

```text
前端：5173
后端：37800
```

如果后端端口冲突，可以覆盖：

```bash
sudo OWLSOME_BACKEND_PORT=39000 bash deployment/systemd/install_owlsome_services.sh
```

手动启动方式保留在下文，主要用于排障。

## 推荐服务器目录

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/ZhouYinLong-lab/Owlsome.git
cd Owlsome
```

已有仓库时只更新：

```bash
cd ~/projects/Owlsome
git pull
```

## 后端环境配置

```bash
cd ~/projects/Owlsome/learning_platform/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

复制服务器环境变量模板并修改：

```bash
cp .env.server.example .env
```

编辑 `.env`，**必须修改**：

```env
ADMIN_TOKEN=your-server-test-token
```

`your-server-test-token` 换成队友知道的字符串，例如 `owlsome2024test`。

如果服务器要跑 LLM 增强问答，同时填写 `LLM_API_KEY` 等字段。

## 准备演示数据

```bash
cd ~/projects/Owlsome/learning_platform/backend
python scripts/seed_demo.py --all
```

可选全书导入：

```bash
# 先 dry-run 看统计
python scripts/import_calculus_full.py --dry-run --report ../../docs/test_records/calculus_full_import_report.md

# 确认后导入
python scripts/import_calculus_full.py --import --reset-course
```

## 启动后端

```bash
cd ~/projects/Owlsome/learning_platform/backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 37800
```

- `--host 0.0.0.0` 允许校园网内其他设备访问。
- 端口 37800 需要在服务器防火墙或外层网关中放行；如果通过 Nginx Proxy Manager 反代，只需要让 `/api` 转发到本机 `37800`。

健康检查：

```bash
curl http://localhost:37800/api/health
```

期望返回 `{"ok":true,"service":"learning_platform"}`。

## 前端配置

复制服务器前端环境变量模板：

```bash
cd ~/projects/Owlsome/learning_platform/frontend
cp .env.server.example .env.production
```

编辑 `.env.production`，填入服务器实际 IP 或域名：

```env
VITE_API_BASE_URL=http://<服务器IP或域名>:37800
```

例如：

```env
VITE_API_BASE_URL=http://10.0.1.50:37800
VITE_API_BASE_URL=http://lilystudio.space:37800
```

构建和启动：

```bash
npm install
npm run build
npm run preview -- --host 0.0.0.0 --port 5173
```

`npm run preview` 是 Vite 内置的静态文件预览服务器，适合快速测试。

## 后台运行方式

### 方式一：zellij（推荐）

```bash
# 安装 zellij（如未安装）
# 或使用 cargo: cargo install zellij

zellij
```

在 zellij 会话中分别启动后端和前端。

**Detach（保持服务运行）：**

```
Ctrl+O, 然后按 D
```

⚠️ **不要直接按 Ctrl+Q**，可能会退出会话或关闭服务。

重新进入：

```bash
zellij attach
```

### 方式二：tmux（备用）

```bash
tmux new -s owlsome
```

在 tmux 会话中启动服务。

**Detach：**

```
Ctrl+B, 然后按 D
```

重新进入：

```bash
tmux attach -t owlsome
```

## 更新代码

```bash
cd ~/projects/Owlsome
git pull
```

然后：

- 后端：重启 uvicorn（Ctrl+C 后重新启动）。
- 前端：重新 `npm run build`，然后重启 `npm run preview`。

## 访问地址

队友在校园网内访问：

- 前端页面：`http://<服务器IP>:5173`
- 后端 API：`http://<服务器IP>:37800`

如果使用 Nginx Proxy Manager 子域名反代，推荐配置：

```text
https://owlsome.lilystudio.space/      -> 192.168.6.152:5173
https://owlsome.lilystudio.space/api/  -> 192.168.6.152:37800/api/
```

## 管理员操作

1. 打开前端页面。
2. 左下角点击"切换为管理员"。
3. 首次切换会弹出 token 输入框。
4. 输入服务器 `.env` 中配置的 `ADMIN_TOKEN`。
5. 点击"确认并切换"。
6. token 保存在浏览器 localStorage，下次无需重新输入。
7. 如果 token 不正确，管理员写操作会返回错误提示。

## 常见问题

### `ModuleNotFoundError: No module named 'app'`

必须在 `learning_platform/backend` 目录下运行 uvicorn：

```bash
cd ~/projects/Owlsome/learning_platform/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 37800
```

### 端口被占用

```bash
# 查看端口占用
lsof -i :37800
# 或
ss -tlnp | grep 37800

# 终止占用进程后重试
```

### 前端无法连接后端

1. 确认后端在运行：`curl http://localhost:37800/api/health`
2. 确认 `.env.production` 中 `VITE_API_BASE_URL` 配置正确。
3. 确认服务器防火墙放行 37800 和 5173 端口。
4. 在浏览器中打开开发者工具，查看网络请求是否 CORS 报错。

### 管理员操作返回 403

1. 服务器 `.env` 中 `ADMIN_TOKEN` 是否正确配置。
2. 前端是否在管理员模式下填写了正确的 token。
3. 可重新切换管理员模式，重新输入 token。

### 管理员操作返回 400（非 403）

400 是业务错误（如数据不存在），非 token 问题。后端错误信息会包含在响应体中。

### SQLite 数据如何重置

```bash
cd ~/projects/Owlsome/learning_platform/backend
python scripts/seed_demo.py --all
```

这会备份旧数据库并重建。

### 如何查看当前 git commit

```bash
cd ~/projects/Owlsome
git log --oneline -1
```

## 安全提醒

- 🔒 **不提交 `.env`**：`.env` 包含 `ADMIN_TOKEN` 和可能填写的 API Key，已在 `.gitignore` 中排除。
- 🔒 **不提交 `*.db`**：SQLite 数据库文件已在 `.gitignore` 中排除。
- 🔒 **不提交 `dist`**：前端构建产物已在 `.gitignore` 中排除。
- ⚠️ **校园网测试 ≠ 正式生产安全**：当前方案仅用于团队内部测试。
- ⚠️ **管理员 token 是 v0.1 临时护栏**：不是登录系统，不能防御重放、中间人等攻击。
- ⚠️ **所有队友共享同一个 token**：仅用于防止路人误操作，不区分管理员身份。
