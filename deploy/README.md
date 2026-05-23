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

## 不想买服务器？可选方案对比

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
