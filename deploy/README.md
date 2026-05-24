# OPC Studio 部署指南

## 架构要点

| 组件 | 说明 |
|------|------|
| 代码 | Git 仓库，版本见根目录 `VERSION` |
| 运行时数据 | `data/`（SQLite + 项目文件），**与代码分离，升级必备份** |
| 进程 | `./start.sh` 或 systemd + uvicorn |
| 前端 | 静态页由 FastAPI 托管，无需单独 Nginx（单机够用） |

---

## 本地 / 内网（当前方式）

```bash
cp .env.example .env          # 首次：设置 OPC_SECRET_KEY
./start.sh
# http://127.0.0.1:8765/dashboards/app/
```

### macOS 后台常驻

项目在 `~/Documents` 时，LaunchAgent 常因系统隐私限制无法执行；安装脚本会自动降级为 nohup 守护进程：

```bash
./deploy/macos/install.sh     # 安装依赖 + 启动 + 健康检查
./deploy/macos/stop.sh        # 停止
# 日志：data/logs/opc-studio.{out,err}.log
```

**升级四步：**

```bash
./scripts/backup-data.sh
git pull
source .venv/bin/activate && pip install -e backend/
./start.sh
curl -s http://127.0.0.1:8765/api/v1/health
```

**发版前：**

```bash
./scripts/release-check.sh
git tag v$(cat VERSION)
```

---

## GitHub → 云端（推荐 Render）

本项目是 **FastAPI + SQLite + 本地文件**，与 Vercel / Cloudflare Pages 的静态或 Serverless 模型不兼容：

| 平台 | 免费域名 | 能否跑整套 OPC Studio |
|------|----------|------------------------|
| **Render** | `*.onrender.com` | ✅ Docker（Free 无持久盘，演示可用） |
| **Fly.io** | `*.fly.dev` | ✅ Docker + Volume |
| Vercel | `*.vercel.app` | ❌ 无持久 SQLite |
| Cloudflare Pages | `*.pages.dev` | ❌ 仅静态页 |
| Cloudflare Workers | — | ❌ 需重写存储层 |

### 一键：Render Blueprint（从 GitHub）

1. 把代码推到 GitHub（`main` 或你的发布分支）
2. 打开 [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
3. 连接仓库 `simmon-clap/opc-studio`，选中根目录 `render.yaml`
4. 部署完成后访问 `https://opc-studio.onrender.com/dashboards/app/`
5. 在 Render 环境变量中可选设置 `OPC_ACCESS_TOKEN`（公网鉴权）

`render.yaml` 已配置：Docker 构建、健康检查、`OPC_SECRET_KEY` 自动生成。Free 档不含持久盘，重新部署后 SQLite 会重置；需长期数据请升级 Render 付费档并加 `disk` 块，或改用 Fly.io Volume。

### 备选：Fly.io（GitHub Actions）

```bash
# 本地首次
brew install flyctl
fly auth login
fly launch --no-deploy    # 按提示创建 app + volume
fly secrets set OPC_SECRET_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
fly deploy
```

自动部署：在 GitHub 仓库 Settings → Secrets 添加 `FLY_API_TOKEN`，推送 `main` 触发 `.github/workflows/deploy-fly.yml`。

### Cloudflare 能做什么？

- **临时演示 URL**：本机 `./start.sh` + `cloudflared tunnel --url http://127.0.0.1:8765` → 随机 `*.trycloudflare.com`（见下方 Tunnel 章节）
- **自有域名 HTTPS**：Render/Fly 部署好后，在 Cloudflare DNS 把 `studio.yourdomain.com` CNAME 到 Render/Fly 提供的地址
- **不能** 仅用 Cloudflare Pages 跑 API + SQLite

---

| 方案 | 费用 | 适合 | 限制 |
|------|------|------|------|
| **Cloudflare Tunnel** | 免费 | 有域名、机器常开（Mac/旧电脑） | 要有一台跑 `./start.sh` 的机器在线 |
| **Tailscale Serve** | 免费额度 | 仅自己/团队内网访问 | 不公开互联网 |
| **Render / Railway / Fly.io** | 约 $5–7/月起 | 不想管机器 | 需持久盘存 SQLite；冷启动慢 |
| **Cloudflare Workers/Pages** | 免费 | 纯静态 | **不适合**本栈（FastAPI+SQLite+本地文件） |
| **VPS（1C2G）** | 约 ¥30–50/月 | 7×24 稳定公网 | 需自己维护 systemd |

### 推荐路径

1. **现在**：本地 `./start.sh` + 定期 `backup-data.sh`
2. **临时外网演示**：`cloudflared tunnel --url http://127.0.0.1:8765`（见 `deploy/cloudflare/setup-tunnel.sh`）
3. **长期公网**：小 VPS + systemd + Caddy HTTPS，或 Fly.io + Volume
4. **不要指望** 纯 Cloudflare Pages/Workers 跑整套后端——除非重写存储层（D1/R2）

---

## Cloudflare Tunnel（免公网 IP）

```bash
# 终端 1
./start.sh

# 终端 2 — 临时公网 URL（免费）
cloudflared tunnel --url http://127.0.0.1:8765
```

稳定域名：复制 `deploy/cloudflare/tunnel.yml.example` → `tunnel.yml`，按 `setup-tunnel.sh` 说明配置。

**上公网前务必：**

- `.env` 设置强随机 `OPC_SECRET_KEY`
- 设置 `OPC_ACCESS_TOKEN`（见 `.env.example`）并在反向代理或应用层校验
- 仅暴露 HTTPS（Tunnel 自带）

---

## Linux VPS（systemd）

```bash
sudo useradd -r -m -d /opt/opc-studio opc || true
sudo git clone <repo> /opt/opc-studio
sudo chown -R opc:opc /opt/opc-studio
cd /opt/opc-studio && sudo -u opc python3 -m venv .venv
sudo -u opc .venv/bin/pip install -e backend/
sudo cp deploy/systemd/opc-studio.service /etc/systemd/system/
sudo systemctl enable --now opc-studio
```

HTTPS：前面加 Caddy 反代 `127.0.0.1:8765`。

---

## 数据备份

```bash
./scripts/backup-data.sh
# → backups/opc-data-YYYYMMDD-HHMMSS.tar.gz
```

恢复：停服务 → 解压到 `data/` → 启动。
