# Owlsome Learning — systemd 服务托管指南

> **适用场景：** 校园网测试部署，替代 zellij/tmux 手动挂起。
> **不是最终公网生产部署方案。**

---

## 1. 推荐一键方式

在服务器仓库根目录执行：

```bash
cd /data/workspace/projects/Owlsome
sudo bash deployment/systemd/install_owlsome_services.sh
```

当前校园网测试默认端口：

```text
前端：5173
后端：37800
```

如果后端端口再次冲突，可以临时覆盖：

```bash
sudo OWLSOME_BACKEND_PORT=39000 bash deployment/systemd/install_owlsome_services.sh
```

脚本会自动完成：

- 创建/复用后端 `.venv` 并安装 `requirements.txt`。
- 首次部署时从 `.env.server.example` 创建后端 `.env`，并生成随机 `ADMIN_TOKEN`。
- 首次部署时从 `.env.server.example` 创建前端 `.env.production`。
- 安装前端依赖并执行 `npm run build`。
- 根据当前仓库路径、Python venv 路径和 npm 路径生成真实 systemd service。
- 启用并重启 `owlsome-backend` 与 `owlsome-frontend`。
- 验证 `http://127.0.0.1:37800/api/health` 和 `http://127.0.0.1:5173`。

更新代码后的最短流程：

```bash
cd /data/workspace/projects/Owlsome
git pull
sudo bash deployment/systemd/install_owlsome_services.sh
```

> 下文保留手动方式，主要用于排障、高级定制或脚本执行失败后的人工修复。

---

## 2. 适用场景

- 校园网 / 内网服务器试部署，供队友访问测试。
- 替代 `zellij attach` / `tmux attach` 手工挂起。
- 避免 SSH 断开、终端关闭、进程崩溃或服务器重启后服务停止，导致 Nginx Proxy Manager 返回 **502 Bad Gateway**。

**不适用：**

- 正式公网生产环境（生产环境建议 Nginx/Caddy 静态托管前端 + Gunicorn/uWSGI + HTTPS + 真实身份认证）。
- Docker 部署（当前仓库未引入 Docker）。

---

## 3. 前置条件

在配置 systemd 之前，请确认以下条件全部满足：

- [ ] 仓库已 clone 到服务器。
- [ ] 后端 Python 虚拟环境已创建并安装依赖。
- [ ] 前端依赖已安装（`npm install`）。
- [ ] 后端 `.env` 已从 `.env.server.example` 复制并设置了 `ADMIN_TOKEN`。
- [ ] 前端已执行 `npm run build`。
- [ ] 当前后端可以通过 `uvicorn` 手动跑通。
- [ ] 当前前端可以通过 `npm run preview` 手动跑通。

验证命令：

```bash
# 后端健康检查
curl http://127.0.0.1:37800/api/health
# 期望返回 {"ok":true,"service":"learning_platform"}

# 前端预览检查
curl http://127.0.0.1:5173
# 期望返回 HTML 页面
```

---

## 4. 确认路径

本指南假定服务器部署路径为：

```
/data/workspace/projects/Owlsome
```

如果你的实际路径不同，需要在后续所有步骤中替换。

确认当前路径和工具位置：

```bash
cd /data/workspace/projects/Owlsome
pwd

which npm

cd learning_platform/backend
source .venv/bin/activate
which python

# 退出 venv
deactivate
```

**⚠️ 如果 `pwd` 输出不是 `/data/workspace/projects/Owlsome`，或 `which npm` / `which python` 路径与 service 模板不一致，必须修改模板中的对应路径。**

需要替换的字段：

| 字段 | 说明 |
|---|---|
| `WorkingDirectory` | 项目根目录下的后端/前端子目录 |
| `EnvironmentFile` | 后端 `.env` 文件的绝对路径 |
| `ExecStart` | Python 解释器路径（后端）/ npm 路径（前端） |
| `Environment=PATH=...` | 前端 service 中 Node/npm 的 PATH |
| `--port` | 端口号（默认 37800 / 5173，如有冲突需修改） |

---

## 5. 复制 service 文件

将仓库中的模板复制到 systemd 系统目录：

```bash
cd /data/workspace/projects/Owlsome

sudo cp deployment/systemd/owlsome-backend.service.example \
  /etc/systemd/system/owlsome-backend.service

sudo cp deployment/systemd/owlsome-frontend.service.example \
  /etc/systemd/system/owlsome-frontend.service
```

---

## 6. 编辑 service 文件

复制后**必须**打开检查路径是否正确：

```bash
sudo nano /etc/systemd/system/owlsome-backend.service
sudo nano /etc/systemd/system/owlsome-frontend.service
```

重点检查项：

- [ ] `WorkingDirectory` 是否指向正确的目录。
- [ ] `EnvironmentFile` 是否指向正确的 `.env` 文件。
- [ ] `ExecStart` 中的 Python venv 路径是否正确。
- [ ] `ExecStart` 中的 npm 路径是否正确。
- [ ] 前端 service 的 `Environment=PATH=...` 是否包含 npm/node 所在目录。
- [ ] 端口 37800 / 5173 是否未被占用。

---

## 7. 启动服务

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 设置开机自启
sudo systemctl enable owlsome-backend
sudo systemctl enable owlsome-frontend

# 启动服务
sudo systemctl start owlsome-backend
sudo systemctl start owlsome-frontend
```

验证启动成功：

```bash
# 等待 2 秒后检查
sleep 2
curl http://127.0.0.1:37800/api/health
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173
```

后端期望返回 `{"ok":true,"service":"learning_platform"}`，前端期望返回 HTTP `200`。

---

## 8. 查看状态

```bash
sudo systemctl status owlsome-backend
sudo systemctl status owlsome-frontend
```

正常输出应包含 `active (running)`。

---

## 9. 查看日志

```bash
# 实时跟踪日志（Ctrl+C 退出）
sudo journalctl -u owlsome-backend -f
sudo journalctl -u owlsome-frontend -f

# 查看最近 100 行
sudo journalctl -u owlsome-backend -n 100
sudo journalctl -u owlsome-frontend -n 100

# 查看本次启动以来的日志
sudo journalctl -u owlsome-backend -b
```

---

## 10. 重启服务

```bash
sudo systemctl restart owlsome-backend
sudo systemctl restart owlsome-frontend
```

---

## 11. 停止服务

```bash
sudo systemctl stop owlsome-backend
sudo systemctl stop owlsome-frontend

# 同时禁用开机自启（如需）
sudo systemctl disable owlsome-backend
sudo systemctl disable owlsome-frontend
```

---

## 12. 更新代码后的操作

推荐直接重新运行一键脚本：

```bash
cd /data/workspace/projects/Owlsome
git pull
sudo bash deployment/systemd/install_owlsome_services.sh
```

如果需要手动更新，每次 `git pull` 更新代码后，执行以下步骤：


```bash
cd /data/workspace/projects/Owlsome
git pull

# 后端（如果 requirements.txt 有变化）
cd learning_platform/backend
source .venv/bin/activate
pip install -r requirements.txt
deactivate

# 前端
cd ../frontend
npm install
npm run build

# 重启服务
sudo systemctl restart owlsome-backend
sudo systemctl restart owlsome-frontend

# 确认服务恢复
sudo systemctl status owlsome-backend owlsome-frontend
```

---

## 13. 常见问题

### 13.1 502 Bad Gateway

Nginx Proxy Manager 返回 502，说明前端或后端服务未正常运行。

**可能原因：**

1. 前端 5173 端口没起来。
2. 后端 37800 端口没起来。
3. Nginx Proxy Manager 转发目标 IP:端口配置错误。

**排查步骤：**

```bash
# 1. 检查端口是否在监听
ss -lntp | grep -E ':5173|:37800'

# 2. 直接 curl 测试
curl http://127.0.0.1:5173
curl http://127.0.0.1:37800/api/health

# 3. 查看服务日志
sudo journalctl -u owlsome-frontend -n 80
sudo journalctl -u owlsome-backend -n 80

# 4. 检查服务状态
sudo systemctl status owlsome-backend owlsome-frontend
```

### 13.2 npm 路径不对

如果 systemd 日志报 `ExecStart: command not found`：

```bash
which npm
```

然后将输出路径（例如 `/usr/local/bin/npm`）替换到 `owlsome-frontend.service` 的 `ExecStart` 中：

```
ExecStart=/usr/local/bin/npm run preview -- --host 0.0.0.0 --port 5173
```

同时确保 `Environment=PATH=...` 中包含 npm 所在目录，例如：

```
Environment=PATH=/usr/local/bin:/usr/bin:/bin
```

修改后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart owlsome-frontend
```

### 13.3 Python venv 路径不对

如果 systemd 日志报 python 找不到：

```bash
cd /data/workspace/projects/Owlsome/learning_platform/backend
source .venv/bin/activate
which python
```

将输出的 Python 绝对路径替换到 `owlsome-backend.service` 的 `ExecStart` 中：

```
ExecStart=/home/user/.local/share/pyenv/versions/3.11.0/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 37800
```

修改后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart owlsome-backend
```

### 13.4 .env 不存在

如果 `EnvironmentFile` 指向的 `.env` 文件不存在，systemd 会报错。

```bash
cd /data/workspace/projects/Owlsome/learning_platform/backend
ls -la .env
```

如果不存在：

```bash
cp .env.server.example .env
nano .env
# 至少填写 ADMIN_TOKEN
```

然后重启后端：

```bash
sudo systemctl restart owlsome-backend
```

### 13.5 端口被占用

```bash
ss -lntp | grep -E ':5173|:37800'
```

如果端口已被占用，可以：
- 终止占用进程后重启服务。
- 或在 service 文件中修改 `--port` 参数（同时调整 Nginx Proxy Manager 转发目标）。

### 13.6 修改前端后没生效

Vite preview 是静态文件服务，修改源码后必须重新构建：

```bash
cd /data/workspace/projects/Owlsome/learning_platform/frontend
npm run build
sudo systemctl restart owlsome-frontend
```

### 13.7 服务启动后立即退出

查看退出原因：

```bash
sudo systemctl status owlsome-backend
# 或
sudo journalctl -u owlsome-backend -n 30
```

常见原因：
- Python 虚拟环境未创建或路径错误。
- `.env` 中 `ADMIN_TOKEN` 缺失。
- 端口被占用。
- 依赖未安装（`pip install -r requirements.txt`）。

### 13.8 非 root 用户运行

以上示例均使用 `sudo`。如果你希望以特定用户（如 `ubuntu`）运行服务，在 `[Service]` 中添加：

```
User=ubuntu
Group=ubuntu
```

注意该用户必须有对应目录的读取和执行权限。

### 13.9 Vite preview 拒绝域名访问

如果访问前端时看到类似错误：

```
Blocked request. This host ("owlsome.lilystudio.space") is not allowed.
```

说明 Vite preview 收到了外层反向代理传入的域名，但该域名没有写入 `vite.config.ts` 的 `preview.allowedHosts`。

处理方式：

```ts
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  },
  preview: {
    allowedHosts: ["owlsome.lilystudio.space"]
  }
});
```

修改后重新构建并重启前端服务：

```bash
cd /data/workspace/projects/Owlsome/learning_platform/frontend
npm run build
sudo systemctl restart owlsome-frontend
```

---

## 安全提醒

- 🔒 **不提交 `.env`**：`.env` 包含 `ADMIN_TOKEN` 和可能填写的 API Key，已在 `.gitignore` 中排除。
- 🔒 **不提交 `*.db`**：SQLite 数据库文件已在 `.gitignore` 中排除。
- 🔒 **不提交 `dist`**：前端构建产物已在 `.gitignore` 中排除。
- ⚠️ **校园网测试 ≠ 正式生产安全**：当前方案仅用于团队内部测试；systemd 只负责进程托管，HTTPS 需要由 Nginx Proxy Manager / Caddy / 其他外层网关提供。
- ⚠️ **systemd 不替代应用层安全**：管理员 token 是 v0.1 临时护栏，不能防御重放、中间人等攻击。
