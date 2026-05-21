# OPC Studio · 后端技术设计（Phase 2）

| 项 | 内容 |
|----|------|
| 版本 | v0.2 草案 |
| 状态 | 技术栈讨论中 · 本地优先 |
| 原则 | **轻量 · 本地优先 · 单用户 · 无 Docker 依赖 · 可备份** |
| 前端基线 | Mock 看板 v0.3（`dashboards/app/`） |

---

## 1. 设计目标

| # | 你的要求 | 设计回应 |
|---|----------|----------|
| 1 | 本地按项目管理，产出物按项目存档 | **文件系统** 存交付物 + **SQLite** 存索引与元数据 |
| 2 | 统计与数据轻量化 | **SQLite 单文件**，无 Redis/Postgres；聚合表按需物化 |
| 3 | 接飞书、微信对话 | **Channel Adapter** 统一入口，Webhook 收消息 → CEO 中枢 |
| 4 | 各角色配置 URL + API Key | **role_config** 表 + 加密存储 + 设置页 CRUD |
| 5 | 方便部署、健壮 | **本地：Python + start.sh**；云端可选（同命令，无需 Docker） |

**明确不做（Phase 2）：**

- 多租户 / 用户登录体系（**本地单用户，绑定 127.0.0.1**）
- Docker 作为必选项（**可选**，本地可不装）
- K8s / 微服务拆分
- 重型消息队列（先用 SQLite + 内存队列即可）
- 个人微信接入（若做微信，走官方绑定能力；**Phase 2 先做飞书**）

---

## 2. 推荐技术栈

```
┌─────────────────────────────────────────────────────────┐
│  dashboards/app/          静态前端（现有，改读 API）      │
└────────────────────────────┬────────────────────────────┘
                             │ REST + SSE
┌────────────────────────────▼────────────────────────────┐
│  FastAPI 0.11x                                            │
│  ├── REST API（dashboard / projects / inbox / finance）   │
│  ├── SSE（角色状态、收件箱、任务进度推送）                  │
│  ├── Webhook（/channels/feishu · 微信 Phase 2.x 预留）       │
│  └── BackgroundTasks / APScheduler（周报定时、成本 rollup） │
└─────┬───────────────────────┬─────────────────────────────┘
      │                       │
┌─────▼──────┐         ┌──────▼──────────────────────────────┐
│ SQLite     │         │ 本地文件系统 data/                    │
│ opc.db     │         │  projects/{id}/artifacts/             │
│            │         │  projects/{id}/deliveries/            │
└────────────┘         │  exports/ · logs/                     │
                       └───────────────────────────────────────┘
```

| 层 | 选型 | 理由 |
|----|------|------|
| 运行时 | Python 3.11+ | Agent 生态、LLM SDK、与你现有习惯一致 |
| Web | **FastAPI** | 异步 Webhook、OpenAPI 文档、类型友好 |
| ORM | **SQLModel**（或 sqlite3 + 薄封装） | 轻量，一张库够用 |
| 数据库 | **SQLite** | 零运维，备份 = 复制一个文件 |
| 文件 | **本地目录** | 产出物原文不进 DB，只存路径与 hash |
| 密钥 | **Fernet 加密** + 环境变量 `OPC_SECRET_KEY` | API Key 不落明文 |
| HTTP 客户端 | **httpx** | 调 LLM API、飞书/企微 API |
| 部署（本地） | **uvicorn + start.sh** | 与现有 Mock 启动方式一致，无 Docker |
| 部署（云端，可选） | 同进程 + systemd + Caddy HTTPS | 以后上云时再加，代码不变 |
| 进程 | **uvicorn** + `--workers 1` | SQLite 写并发简单，单 worker 足够 |

Phase 3 再引入：**LangGraph / 自研 YAML Runner** 跑真 Agent，与 Phase 2 API 解耦。

---

## 3. 目录结构（建议）

```
opc-agent-framework/
├── data/                          # ★ 本地数据根（gitignore，部署时挂卷）
│   ├── opc.db
│   └── projects/
│       └── proj-acme/
│           ├── meta.json          # 可选冗余快照
│           ├── artifacts/
│           │   ├── art-prd-acme.md
│           │   └── art-demo-acme.md
│           └── deliveries/
│               └── 2026-05-21_client.zip
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py              # 环境变量、路径
│   │   ├── db.py                  # SQLite 连接
│   │   ├── models/                # SQLModel 表
│   │   ├── api/
│   │   │   ├── dashboard.py       # GET /api/dashboard（聚合，兼容现有 JSON 形状）
│   │   │   ├── projects.py
│   │   │   ├── artifacts.py
│   │   │   ├── inbox.py
│   │   │   ├── finance.py
│   │   │   ├── weekly.py
│   │   │   ├── roles.py           # 角色配置 CRUD
│   │   │   └── events.py          # SSE
│   │   ├── channels/
│   │   │   ├── base.py            # ChannelAdapter 接口
│   │   │   ├── feishu.py
│   │   │   └── wechat.py          # 企业微信
│   │   ├── services/
│   │   │   ├── project_store.py   # 项目文件读写
│   │   │   ├── finance.py         # 成本 rollup、项目 P&L
│   │   │   └── ceo_router.py      # 消息 → inbox / thread
│   │   └── security/
│   │       └── secrets.py         # API Key 加解密
│   └── tests/
├── dashboards/app/                # 前端 fetch('/api/dashboard')
├── mock/dashboard.json            # Phase 2 迁移种子数据
├── docker-compose.yml
└── docs/
    ├── PRD.md
    └── BACKEND.md                 # 本文档
```

---

## 4. 数据模型

### 4.1 SQLite 表（核心）

```sql
-- 项目（元数据；大文件走 filesystem）
projects (
  id, client_id, client_name, summary, pipeline_column,
  stage, progress, priority, contract_amount,
  closure_status, created_at, updated_at
)

-- 客户
clients (
  id, name, contact, industry, status,
  total_revenue, received, notes_json
)

-- 产出物索引（正文路径在磁盘）
artifacts (
  id, project_id, type, title, version,
  file_path,           -- data/projects/{pid}/artifacts/{id}.md
  role_id, demo_url, content_hash, updated_at
)

-- 任务 & 活动流
tasks ( id, role_id, project_id, title, status, priority, ... )
task_activities ( id, task_id, at, message )

-- 收件箱 & HITL
inbox_items ( id, category, channel, title, preview, status, ... )
hitl_queue ( id, type, project_id, approved, ... )
reject_history ( ... )

-- CEO 对话
ceo_messages ( id, direction, channel, text, at )

-- 角色配置 ★
role_config (
  role_id PRIMARY KEY,
  model, api_provider,
  api_base_url,          -- 各角色可不同 OpenRouter / 直连 / 本地 Ollama
  api_key_encrypted,     -- Fernet 密文
  monthly_budget, tools_json
)

-- Token 成本（按 run 记账，rollup 到项目）
token_runs (
  id, role_id, project_id, model,
  input_tokens, output_tokens, cost_cny, at
)

-- 项目盈亏快照（可 nightly 重算，也可查询时聚合）
-- 初期：查询时 SUM(token_runs) JOIN projects，不必单独表

-- 结项清单
closure_checklists ( project_id, items_json, status, closed_at )

-- 渠道配置
channel_config (
  channel,               -- feishu | wechat
  enabled, app_id, app_secret_encrypted,
  verification_token, encrypt_key, webhook_path
)
```

### 4.2 文件系统约定

**原则：** DB 存「是什么、在哪、谁改的」；磁盘存「内容本身」。

```
data/projects/{project_id}/
├── artifacts/
│   └── {artifact_id}.md          # 或 .pdf / .json
├── deliveries/
│   └── {date}_client.zip
└── uploads/                      # Founder 上传的客户样本等
    └── invoice-samples/
```

**创建项目时** 自动 `mkdir -p data/projects/{id}/artifacts`。

**读取工作室：** `GET /api/projects/{id}/artifacts` → 列表来自 DB，正文 `GET .../artifacts/{aid}/content` 读文件。

**导出 ZIP：** 服务端打包 `artifacts/` + 生成 `deliveries/`，并写 inbox 通知。

---

## 5. API 设计（与前端 Mock 对齐）

Phase 2 第一步：**一个聚合接口** 让现有前端最小改动：

```
GET  /api/dashboard              → 与 mock/dashboard.json 同结构
GET  /api/events                 → SSE 推送 diff
```

随后拆细：

| 域 | 方法 | 路径 | 说明 |
|----|------|------|------|
| 项目 | CRUD | `/api/projects` | 创建时建目录 |
| 产出 | GET/POST/PUT | `/api/projects/{id}/artifacts` | 写文件 + 更新 DB |
| 收件箱 | GET/PATCH | `/api/inbox` | 已读、归档、批准 |
| HITL | POST | `/api/hitl/{id}/approve` | 触发结项状态机 |
| 经营 | GET | `/api/finance/summary` | 收入/成本/毛利/项目 P&L |
| 周报 | GET/POST | `/api/weekly` | 生成、发送 |
| 角色 | GET/PUT | `/api/roles/config` | URL + API Key（返回时 Key 打码） |
| 渠道 | GET/PUT | `/api/channels/config` | 飞书/企微凭证 |
| 健康 | GET | `/health` | Docker healthcheck |

**SSE 事件类型：** `role.updated` · `inbox.new` · `task.progress` · `finance.updated`

---

## 6. 渠道接入（飞书优先 · 微信后置）

### 6.0 分期策略

| 阶段 | 渠道 | 说明 |
|------|------|------|
| Phase 2a–c | **Web 看板 + CEO FAB** | 不依赖公网，本地即可 |
| Phase 2d | **飞书** | 企业自建应用 + 事件订阅；需模式 B 或 C 的公网 URL |
| Phase 2.x+ | **微信（可选）** | 按官方绑定方式单独设计；接口预留，不阻塞主线 |

**建议：先做飞书，微信等你有明确绑定方案再加。** Channel Adapter 已抽象，后加微信不改 CEO 中枢逻辑。

### 6.1 统一消息模型

```python
class InboundMessage:
    channel: Literal["feishu", "wechat", "web"]
    sender_id: str
    text: str
    raw: dict
    at: datetime

class OutboundMessage:
    channel: str
    recipient_id: str
    text: str
```

### 6.2 数据流

```
飞书/企微用户 @CEO
    → POST /channels/feishu/webhook
    → verify signature
    → ceo_router.ingest(msg)
        → append ceo_messages
        → 可选：触发 CEO Agent（Phase 3）
        → 写入 inbox（must_read / request）
    → 回复用户（渠道 API）

Web 看板 CEO FAB
    → POST /api/ceo/brief
    → 同上 ceo_router（channel=web）
```

### 6.3 实现要点

| 渠道 | 接入方式 | 备注 |
|------|----------|------|
| **飞书** | 企业自建应用 + 事件订阅 Webhook | 本地开发：ngrok；上云：固定域名 |
| **微信** | 待定（公众号/企微/开放能力） | Phase 2.x，单独 PRD 条目 |
| **Web** | CEO FAB + REST | 默认渠道，本地可用 |

**健壮性：**

- Webhook 处理 **先 ACK 再异步**（BackgroundTasks），防飞书超时重试
- `inbound_messages` 表记录原始 payload，幂等 `message_id`
- 渠道凭证加密存储，与 role API Key 同一套 `secrets.py`

---

## 7. 角色 LLM 配置

```yaml
# 示例：role_config 运行时解析
ceo:
  api_base_url: https://openrouter.ai/api/v1
  api_key: "***"          # 界面只显示末 4 位
  model: openai/gpt-4o
  monthly_budget: 800

dev:
  api_base_url: https://api.anthropic.com/v1   # 可不同厂商
  api_key: "***"
  model: claude-sonnet-4-20250514
  monthly_budget: 2000
```

**调用路径（Phase 3）：**

```
Agent Runner
  → load role_config[role_id]
  → decrypt api_key
  → httpx.post(f"{api_base_url}/chat/completions", ...)
  → log token_runs(role_id, project_id, tokens, cost)
  → rollup → finance API → 前端经营页
```

**安全：**

- `OPC_SECRET_KEY` 只在 `.env` / Docker secrets，不入库明文
- 设置页 PUT 时全量替换 Key；GET 永不返回完整 Key
- 可选：macOS Keychain 集成为 Phase 2.1

---

## 8. 统计与项目盈亏

**记账时机：** 每次 LLM 调用后 insert `token_runs`。

**聚合（SQL 示例）：**

```sql
SELECT project_id, SUM(cost_cny) AS cost, SUM(input_tokens+output_tokens) AS tokens
FROM token_runs
WHERE at >= date('now', 'start of month')
GROUP BY project_id;
```

**项目 P&L：**

```
margin = projects.contract_amount - SUM(token_runs.cost)   -- 已签约
health = f(received, cost, signed, progress)                -- 与前端 Mock 规则一致
```

**轻量策略：**

- 不做实时 OLAP；月度 summary 可 **启动时 + 每日 00:05** 写 `finance_snapshots` 一行
- 前端继续读 `/api/finance/summary`，形状与 Mock `costs` 一致

---

## 9. 部署方案（本地优先 · Docker 可选）

### 9.1 三种运行模式

| 模式 | 适用 | 启动方式 | 飞书 Webhook |
|------|------|----------|--------------|
| **A · 纯本地（默认）** | 日常管理、Phase 2a–c | `./start.sh` | 暂不接，或开发时用 ngrok |
| **B · 本地 + 隧道** | 要接飞书、仍在本机跑 | `./start.sh` + ngrok/Cloudflare Tunnel | 临时公网 URL 指到本机 |
| **C · 云端（可选）** | 域名、随时随地访问 | VPS 上 `./start.sh` 或 systemd | 稳定 HTTPS 域名 |

**结论：Docker 不是必需。** 它只是模式 C 的一种打包方式；你本地不方便用 Docker，完全可以 **Python 直跑**。上云时也推荐 **systemd + Caddy**（比 Docker 还轻）。

### 9.2 本地运行（推荐 Phase 2 默认）

```bash
# 一次性
cd ~/Documents/opc-agent-framework/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 日常（替代现有 python -m http.server）
cd ~/Documents/opc-agent-framework
./start.sh          # → uvicorn :8765，托管 dashboards + /api
```

- 数据目录：`~/Documents/opc-agent-framework/data/`（SQLite + 项目文件）
- 绑定：`127.0.0.1:8765`（仅本机访问，**无需登录**）
- 备份：复制整个 `data/` 文件夹即可

### 9.3 云端运行（将来可选，代码相同）

```
你的域名 opc.example.com
    → Caddy（自动 HTTPS）
    → uvicorn 127.0.0.1:8765
    → data/ 仍在磁盘上
```

| 项 | 建议 |
|----|------|
| 机器 | 任意 Linux VPS（1C2G 够用） |
| HTTPS | Caddy 反向代理 + Let's Encrypt |
| 进程守护 | systemd `Restart=always`（不必 Docker） |
| 安全 | 仅当你**真的上公网**时，加一层简单 Bearer Token（`.env`）；纯本地不需要 |
| 数据 | `data/` 挂到 VPS 同路径，或 rsync 备份 |

### 9.4 Docker（可选，非默认）

若将来希望在云上一键还原环境，可 **额外** 提供 `docker-compose.yml`，但不作为开发/本地前提。

### 9.5 健壮性清单

| 项 | 做法 |
|----|------|
| 数据不丢 | `data/` 整目录备份（含 opc.db + projects/） |
| 崩溃恢复 | 本地：手动重启 `./start.sh`；云端：systemd 自动重启 |
| DB 损坏 | 启动时 SQLite `PRAGMA integrity_check` |
| 写文件原子性 | 先写 `.tmp` 再 `rename` |
| 日志 | `data/logs/opc.log` 按日滚动 |
| Webhook 重试 | 幂等表 + 去重 |
| 升级 | 手写 `schema_version` 迁移脚本 |

---

## 10. 实施分期

| 阶段 | 交付 | 预估 |
|------|------|------|
| **2a · 骨架** | FastAPI + SQLite + `GET /api/dashboard` + `./start.sh` 托管 | 1–2 周 |
| **2b · 项目存储** | 项目 CRUD、artifacts 文件读写、工作室接 API | 1 周 |
| **2c · 状态机** | inbox / HITL / 结项 / finance rollup | 1 周 |
| **2d · 飞书** | 飞书 Webhook + CEO thread 同步（可选，需公网） | 1 周 |
| **2e · 配置** | 角色 URL/Key 设置页接 API + 加密 | 3–5 天 |
| **2x · 微信** | 按官方绑定方式接入 | 待定 |
| **3 · Agent** | Runner 调 LLM、写 task/activity/token_runs | 后续 |

**2a 验收：** `./start.sh` 启动，浏览器打开看板，数据来自 SQLite + `data/projects/`，功能与 Mock 一致。

---

## 11. 前端改造要点（Phase 2 接 API 时）

```javascript
// app.js 改动最小化
const API = window.location.origin + '/api';
async function init() {
  const res = await fetch(`${API}/dashboard`);
  data = await res.json();
  // 其余 render 逻辑不变
}
// 可选：EventSource(`${API}/events`) 增量刷新
```

---

## 12. 技术栈共识（讨论稿 · 2026-05）

| # | 决策 | 建议 | 你的倾向 |
|---|------|------|----------|
| 1 | 核心栈 | **FastAPI + SQLite + 本地 data/ 目录** | 待确认 |
| 2 | 本地部署 | **不用 Docker**，`./start.sh` + Python venv | ✅ 倾向不用 Docker |
| 3 | 云端 | **可选**，同一套代码 + systemd + Caddy | 可能不上云 |
| 4 | 认证 | **本地无登录**（127.0.0.1）；上公网再加 Token | ✅ 不做登录 |
| 5 | 飞书 | Phase 2d，需隧道或域名 | 可先只做飞书 |
| 6 | 微信 | Phase 2.x 预留，不阻塞 | 后置 |
| 7 | Agent | Phase 3 LangGraph 或 httpx 自研 | 后续 |

**不变的部分（与是否 Docker / 是否上云无关）：**

- SQLite 管索引与统计
- `data/projects/{id}/` 管交付物文件
- 五角色独立 API URL + Key
- 前端继续静态页 + `/api/dashboard`

---

## 13. 关联文档

- [PRD.md](./PRD.md) — 产品需求 v0.3
- [API.md](./API.md) — **前后端 API 契约（开发基准）**
- [architecture.html](../architecture.html) — 业务全景 v3
- [README.md](../README.md) — 启动说明
