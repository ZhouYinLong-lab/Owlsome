 ## 快速命令速查

    # ── 文件操作 ──
    ls          # eza 增强列目录
    l           # eza（忽略 .gitignore）
    ll          # eza -lah（详细+隐藏+人类可读）
    llm         # eza 按修改时间排序的长列表
    la          # eza 超详细全信息
    lx          # eza 超详细 + 扩展属性
    lt          # eza --tree -L 2（树形 2 层）
    tree        # eza --tree

    # ── 编辑/阅读 ──
    md          # micro 编辑器
    glow        # Markdown 终端预览（需安装）

    # ── Git ──
    g           # git
    gs          # git status
    gd          # git diff
    gc          # git commit

    # ── 终端工作区 ──
    zj          # zellij 分屏管理器
    tmux        # 备用分屏

    # ── AI 工具 ──
    c           # claude（Claude Code）
    oc          # opencode（OpenCode）

    # ── 智能导航 ──
    z DIR       # zoxide 智能跳转（如 z workspace）
    rg KEYWORD  # ripgrep 全文搜索
    fd NAME     # fd 文件搜索
    fzf         # 模糊查找（常配合 fd | fzf）

    # ── Python ──
    uv venv                     # 创建虚拟环境
    uv pip install PKG          # 安装包
    uv python install 3.12      # 安装 Python 版本

    # ── Node.js ──
    npm install
    pnpm install

    # ── Docker ──
    docker ps
    docker compose up -d
    docker compose down

    # ── GitHub CLI ──
    gh auth login
    gh repo clone owner/repo
    gh pr list

    # ── 浏览器自动化 ──
    playwright codegen https://example.com

  --------

  ## Oh My Zsh 已启用插件

  以下插件随 shell 启动自动加载，提供额外 alias 和功能：

   插件                               │ 效果
  ────────────────────────────────────┼─────────────────────────────────────
    git  /  gitfast                   │  gst 、 gco 、 gcm  等海量 git
                                      │ alias；分支名补全
    gh                                │  gh  命令补全
    sudo                              │ 按两次  Esc  在当前命令前插入
    history  /  history-substring-    │ 增强历史搜索
   search                             │
    fzf                               │ Ctrl+T 模糊选文件，Ctrl+R
                                      │ 模糊搜历史，Alt+C 模糊进目录
    zoxide                            │  z  命令智能跳转（基于使用频率，比
                                      │  cd  更聪明）
    docker                            │ docker 子命令补全
    tmux                              │ tmux alias 和补全
    python  /  uv  /  rust            │ 语言工具链 alias 和补全
    npm  /  yarn                      │ Node 包管理补全
    extract                           │  extract ARCHIVE  —
                                      │ 万能解压，自动识别格式
    colored-man-pages                 │ man 手册语法高亮
    command-not-found                 │ 输错命令时提示安装来源
    ssh  /  rsync                     │ 远程操作补全
    systemd                           │  systemctl / journalctl  补全
    zsh-eza                           │ eza 增强 ls 的 zsh 集成
    zsh-autosuggestions               │ 灰色自动补全，按  →  接受建议
    fast-syntax-highlighting          │ 命令输入实时语法高亮

  --------

  ## eza 文件管理（完整别名解析）

  zshrc 中最终生效的别名（同名覆盖后）：

   最终别名 │ 展开                           │ 用途
  ──────────┼────────────────────────────────┼──────────────────────────────
    ls      │  eza                           │ 基础替代 ls（彩色、图标）
    l       │  eza --git-ignore              │ 只看已跟踪文件
    ll      │  eza -lah                      │ 日常最常用：详细+隐藏+人类可
            │                                │ 读
    llm     │  eza --all --header --long --  │ 按修改时间排，最近改的在上
            │ sort=modified                  │
    la      │  eza -lbhHigUmuSa              │ 超级详细全部信息
    lx      │  eza -lbhHigUmuSa@             │ la + 扩展属性
    lt      │  eza --tree -L 2               │ 树形 2 层
    tree    │  eza --tree                    │ 完整目录树

  --------

  ## Git 精简命令

    g            # git（直接敲 git 子命令即可）
    gs           # git status
    gd           # git diff
    gc           # git commit（后面加 -m "msg"）

  Oh My Zsh  git  插件额外提供常用 alias： gst (status)、 gco (checkout)、 gcm
  (checkout main)、 gcb (checkout -b)、 gf (fetch)、 gp (push) 等。

  --------

  ## Zellij 分屏工作

    zj          # 启动 / 重新连接

   操作                                │ 按键
  ─────────────────────────────────────┼────────────────────────────────────
   水平分屏                            │  Ctrl+p d
   垂直分屏                            │  Ctrl+p n
   关闭 Pane                           │  Ctrl+p x
   切换 Pane                           │  Alt+方向键
   新建 Tab                            │  Ctrl+p c
   下/上一个 Tab                       │  Ctrl+p l  /  Ctrl+p h
   最大化当前 Pane                     │  Ctrl+p f

  --------

  ## Micro 编辑器

    md FILE.md    # 打开或创建文件

   快捷键                              │ 功能
  ─────────────────────────────────────┼────────────────────────────────────
   Ctrl+S                              │ 保存
   Ctrl+Q                              │ 退出
   Ctrl+F                              │ 搜索
   Ctrl+G                              │ 跳转行
   Ctrl+E                              │ 命令模式（可输入 shell 命令）
   Ctrl+Z                              │ 撤销
   Ctrl+Y                              │ 重做

  --------

  ## AI 编程工具

    c            # 启动 Claude Code（主力）
    oc           # 启动 OpenCode（开源备选）

  典型工作流：

    cd /data/workspace/projects/PROJECT
    c                           # 用 Claude Code 开始开发

  --------

  ## 搜索四件套

    rg KEYWORD               # ripgrep 全文搜索，自动忽略 .gitignore
    fd NAME                  # 文件/目录名搜索，极快
    fd | fzf                 # 模糊交互式选文件
    fzf                      # Ctrl+T 当前目录选文件；Ctrl+R 搜历史；Alt+C
  选目录
    z DIR                    # zoxide 智能跳转（只需打目录名片段）

  --------

  ## 环境变量

   变量                   │ 值                     │ 作用
  ────────────────────────┼────────────────────────┼────────────────────────
    PLAYWRIGHT_BROWSERS_P │  /data/browser/playwri │ Playwright
   ATH                    │ ght                    │ 浏览器安装位置
    UV_CACHE_DIR          │  /data/.uv-cache       │ uv 缓存目录

  --------

  ## 常用组合流

    # 编辑搜索结果中的文件
    micro $(fd .md | fzf)

    # 全文搜 + 预览
    rg "keyword" /data/workspace

    # 跳转项目 + 开 AI
    z nanna && c

    # 跳转 + 分屏开发
    z project && zj

    # 创建 Python 项目一把梭
    mkdir demo && cd demo && uv venv && source .venv/bin/activate && uv pip
  install requests

    # 创建 Node 项目一把梭
    mkdir app && cd app && pnpm init && pnpm install

    # Docker 服务管理
    cd /data/docker && docker compose up -d
