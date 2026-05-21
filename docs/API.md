# OPC Studio · API 契约规范

| 项 | 内容 |
|----|------|
| 版本 | v1.0 |
| 状态 | Phase 2 开发基准 · **前后端一次性对齐** |
| 黄金样本 | [`mock/dashboard.json`](../mock/dashboard.json) |
| 后端实现 | [BACKEND.md](./BACKEND.md) |

---

## 1. 为什么要有这份文档

前端 v0.3 已有 **20+ 数据域、15+ 写操作**（批准 HITL、结项、周报发送等）。若后端边做边猜字段，极易出现：

- 字段名不一致（`hitlPending` vs `hitl_pending`）
- 枚举值对不上（`pipelineColumn` 少一种）
- 写操作后聚合数据未更新（脉搏条、stats、P&L 不同步）
- 结项 / HITL 状态机分支遗漏

**原则：Mock JSON 即契约。** 后端 `GET /api/dashboard` 的响应必须与 `mock/dashboard.json` **结构兼容**；写操作后服务端负责重算衍生字段，再返回 patch 或触发前端刷新。

---

## 2. 通用规范

### 2.1 Base URL

| 环境 | Base |
|------|------|
| 本地 | `http://127.0.0.1:8765` |
| API 前缀 | `/api/v1` |

示例：`GET http://127.0.0.1:8765/api/v1/dashboard`

### 2.2 数据格式

- 请求 / 响应：`application/json; charset=utf-8`
- 时间：**ISO 8601**，带时区，如 `2026-05-21T14:00:00+08:00`
- 金额：整数 **CNY 分** 或整数 **元**（全项目统一；**当前 Mock 用「元」整数**，Phase 2 保持一致）
- ID：字符串，`proj-acme` / `inbox-hitl-1` / `task-ceo-1`
- 空值：可选字段无值时 **省略或 `null`**，前端用 `?.` 防御；不要改字段名

### 2.3 命名

- JSON 字段：**camelCase**（与现有 Mock、前端一致）
- URL 路径：**kebab-case**
- 枚举：字符串字面量，见 §4

### 2.4 响应 Envelope

**成功（单对象）：**

```json
{ "ok": true, "data": { ... } }
```

**成功（列表）：**

```json
{ "ok": true, "data": [ ... ], "meta": { "total": 5 } }
```

**失败：**

```json
{
  "ok": false,
  "error": {
    "code": "HITL_ALREADY_APPROVED",
    "message": "该 HITL 已批准",
    "details": {}
  }
}
```

| HTTP | 含义 |
|------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 409 | 状态冲突（如重复批准） |
| 500 | 服务端错误 |

### 2.5 分页

Phase 2 数据量小，**默认不分页**。`ceoThread`、`task.activities` 可限最近 100 条。

### 2.6 认证

Phase 2 本地：**无 Header**。绑定 `127.0.0.1` 即可。

---

## 3. 架构：读聚合 + 写分散

```
┌─────────────┐     GET /dashboard      ┌─────────────┐
│   前端      │ ◄────────────────────── │   后端      │
│  app.js     │     形状 = Mock JSON    │  FastAPI    │
└──────┬──────┘                         └──────▲──────┘
       │                                        │
       │  POST/PATCH 写操作                      │
       └────────────────────────────────────────┘
                    返回 { ok, data: patch }
                    或 204 + 前端 GET /dashboard
```

**Phase 2a 最小目标：** 仅实现 `GET /api/v1/dashboard`，前端改一行 `fetch` 即可跑通只读。

**Phase 2b–c：** 按 §5 实现写接口；写成功后返回 **DashboardPatch** 或触发全量刷新。

---

## 4. 枚举与常量

### 4.1 角色 `RoleId`

`ceo` | `product` | `legal` | `dev` | `ops`

### 4.2 工作状态 `WorkStatus`

`idle` | `working` | `waiting` | `blocked`

### 4.3 任务状态 `TaskStatus`

`running` | `pending` | `waiting` | `blocked` | `done`

### 4.4 Pipeline 列 `pipelineColumn`

`lead` | `clarify` | `active` | `hitl` | `done`

> 注：项目对象上 `hitlPending` 为 `"HITL-1"`…`"HITL-4"` 字符串或 `null`；统计 filter `hitl` 表示有待批项目。

### 4.5 收件箱 `inbox.category`

`must_read` | `request` | `approval`

### 4.6 收件箱 `inbox.status`

`active` | `done` | `archived`

### 4.7 结项 `closure.status`

`awaiting_hitl` | `in_closure` | `closed`

### 4.8 项目盈亏 `health`

`healthy` | `strong` | `watch` | `pipeline` | `loss`

### 4.9 渠道 `channel`

`feishu` | `wechat` | `web`

### 4.10 周报 `weeklyReport.status`

`draft` | `sent`

### 4.11 客户 `clients.status`

`active` | `prospect` | `renewal` | `lead`

### 4.12 产出物 `artifacts.type`

`prd` | `demo` | `email` | `memo` | `contract` | …

### 4.13 产出物 `artifacts.icon`

`doc` | `link` | `mail`

---

## 5. 接口清单

### 5.1 总览 · 读

| 方法 | 路径 | 说明 | Phase |
|------|------|------|-------|
| GET | `/api/v1/dashboard` | **全量看板数据**，结构 ≡ `mock/dashboard.json` | 2a |
| GET | `/api/v1/health` | `{ "ok": true, "version": "0.1.0" }` | 2a |
| GET | `/api/v1/events` | SSE 推送（见 §7） | 2c |

### 5.2 项目 & 产出物

| 方法 | 路径 | 说明 | Phase |
|------|------|------|-------|
| GET | `/api/v1/projects` | 项目列表（dashboard 子集） | 2b |
| GET | `/api/v1/projects/{id}` | 单项目 + closure 摘要 | 2b |
| GET | `/api/v1/projects/{id}/artifacts` | 产出物列表（不含正文） | 2b |
| GET | `/api/v1/projects/{id}/artifacts/{aid}` | 产出物元数据 | 2b |
| GET | `/api/v1/projects/{id}/artifacts/{aid}/content` | Markdown 正文（读文件） | 2b |
| PUT | `/api/v1/projects/{id}/artifacts/{aid}/content` | 更新正文（Agent/人工） | 2b |
| POST | `/api/v1/projects/{id}/artifacts` | 新建产出物 | 2b |
| GET | `/api/v1/projects/{id}/export` | 下载 ZIP（query: `type=internal\|client`） | 2c |

**文件存储：** 正文不在 JSON 里持久化到 DB；API 读写 `data/projects/{id}/artifacts/{aid}.md`。

### 5.3 客户

| 方法 | 路径 | 说明 | Phase |
|------|------|------|-------|
| GET | `/api/v1/clients` | 客户列表 | 2b |
| GET | `/api/v1/clients/{id}` | 客户详情 + payments + notes | 2b |

### 5.4 收件箱 & HITL

| 方法 | 路径 | 说明 | Phase |
|------|------|------|-------|
| GET | `/api/v1/inbox` | 收件箱（query: `category`, `status`） | 2c |
| PATCH | `/api/v1/inbox/{id}` | 标记已读 / 归档 | 2c |
| POST | `/api/v1/inbox/{id}/resolve` | 请示类：同意 / 再议 | 2c |
| GET | `/api/v1/hitl/{id}` | HITL 详情 | 2c |
| POST | `/api/v1/hitl/{id}/approve` | 批准（见 §6.1 状态机） | 2c |
| POST | `/api/v1/hitl/{id}/reject` | 驳回（body: `{ "note": "..." }`） | 2c |
| GET | `/api/v1/reject-history` | 驳回历史 | 2c |

### 5.5 CEO 通道

| 方法 | 路径 | 说明 | Phase |
|------|------|------|-------|
| GET | `/api/v1/ceo/thread` | 对话线程 | 2c |
| POST | `/api/v1/ceo/brief` | 投递简报（body: `{ "text": "..." }`） | 2c |

### 5.6 经营 & 周报

| 方法 | 路径 | 说明 | Phase |
|------|------|------|-------|
| GET | `/api/v1/finance/summary` | `costs` 对象 | 2c |
| GET | `/api/v1/finance/projects` | `costs.byProject`（含 P&L） | 2c |
| GET | `/api/v1/weekly/current` | 当前周报 | 2c |
| POST | `/api/v1/weekly/current/send` | 发送周报 | 2c |
| GET | `/api/v1/weekly/current/export` | 导出 MD/PDF（query: `format=md\|pdf`） | 2c |

### 5.7 角色 & 设置

| 方法 | 路径 | 说明 | Phase |
|------|------|------|-------|
| GET | `/api/v1/roles` | 角色快照列表 | 2a |
| GET | `/api/v1/roles/{id}/tasks` | 角色任务（running + pending） | 2a |
| GET | `/api/v1/roles/config` | 角色 LLM 配置（**Key 打码**） | 2e |
| PUT | `/api/v1/roles/config/{roleId}` | 更新配置（见 §5.7.1） | 2e |
| GET | `/api/v1/channels/status` | 渠道连接状态 | 2d |

#### 5.7.1 PUT 角色配置 Body

```json
{
  "model": "gpt-4o",
  "apiProvider": "OpenRouter",
  "apiBaseUrl": "https://openrouter.ai/api/v1",
  "apiKey": "sk-xxx",
  "monthlyBudget": 800,
  "tools": ["pipeline", "dispatch", "report"]
}
```

响应中 `apiKey` 仅 `{ "masked": "...x7Kp" }`；完整 Key 永不回传。

### 5.8 飞书（Phase 2d）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/channels/feishu/webhook` | 飞书事件回调（验签） |
| POST | `/api/v1/channels/feishu/send` | 主动发消息（内部用） |

---

## 6. 业务逻辑（后端必须实现）

### 6.1 HITL 批准 `POST /hitl/{id}/approve`

**前置：** `hitlQueue[].approved !== true`

**效果（以 Acme HITL-3 为例，与 Mock 一致）：**

```
hitlQueue[id].approved = true
inbox[hitlId=*].status = "done", resolution = "approved", read = true
pulse.hitlPending -= 1
stats.hitl.value -= 1
project.hitlPending = null
project.progress = 92
project.stage = "阶段5 · 结项交付"
project.closureStatus = "in_closure"
closure[projectId].status = "in_closure"
closure.checklist[HITL-3项].done = true
closure.checklist[验收项].done = true
```

**响应：**

```json
{
  "ok": true,
  "data": {
    "patch": {
      "pulse": { "hitlPending": 0 },
      "projects": [ { "id": "proj-acme", "progress": 92, ... } ],
      "closure": { "proj-acme": { ... } }
    },
    "nextAction": "open_workroom",
    "projectId": "proj-acme"
  }
}
```

### 6.2 HITL 驳回 `POST /hitl/{id}/reject`

```json
// Request
{ "note": "报价区间需下调 10%" }
```

```
rejectHistory.unshift({ hitlId, projectId, type, note, at })
inbox[hitlId=*].status = "done", resolution = "rejected"
```

### 6.3 请示 resolve `POST /inbox/{id}/resolve`

```json
{ "action": "approve" | "discuss" }
```

```
inbox.status = "done"
inbox.resolution = "approved" | "discussed"
inbox.resolvedAt = now()
```

### 6.4 结项 · 客户 ZIP `GET /projects/{id}/export?type=client`

- 打包 `artifacts/` 下文件
- Demo 类型追加 `demoUrl` 到文本
- 写入 `deliveries/` 目录
- 可选：`closure.checklist[ZIP项].done = true`

### 6.5 周报发送 `POST /weekly/current/send`

```
weeklyReport.status = "sent"
inbox[weeklyReportId].read = true, status = "done"
roles[ceo].extras.reportStatus = "本周周报已发送"
```

### 6.6 CEO 简报 `POST /ceo/brief`

```json
{ "text": "客户需求..." }
```

```
ceoThread += founder_to_ceo (channel=web)
ceoThread += ceo_to_founder (type=ack, 固定回复 Mock 文案或 Agent 生成)
// Phase 3: 触发 CEO Agent 更新 pipeline
```

### 6.7 衍生字段重算规则

| 字段 | 计算 |
|------|------|
| `stats.*.value` | 按 `projects` / `inbox` 聚合 |
| `pulse.*` | 同上 |
| `costs.byProject[].cost` | `SUM(token_runs)` 按 project_id |
| `costs.byProject[].margin` | `revenue - cost`（已签约） |
| `costs.byProject[].health` | 规则见 PRD / Mock |
| `roles[].runningCount` | `COUNT(tasks WHERE status=running)` |

**写操作后必须触发重算**，或返回足够 `patch` 供前端合并。

---

## 7. SSE 事件（Phase 2c 可选）

```
GET /api/v1/events
Accept: text/event-stream
```

| event | payload | 触发时机 |
|-------|---------|----------|
| `dashboard.patch` | `{ pulse, inbox, ... }` | 任意写操作后 |
| `inbox.new` | `{ item }` | 新收件 |
| `task.updated` | `{ taskId, progress }` | Agent 进度 |
| `finance.updated` | `{ costs.summary }` | token_runs 新增 |

前端可 Phase 2a 只用轮询 / 写后 `GET /dashboard` 刷新。

---

## 8. Dashboard 响应结构（顶层键）

与 `mock/dashboard.json` **必须包含以下顶层键**：

| 键 | 类型 | 前端用途 |
|----|------|----------|
| `meta` | object | 公司名、版本 |
| `pulse` | object | 概览脉搏条 |
| `stats` | object | 项目 Tab 统计 chips |
| `roles` | array | 概览节点、角色弹窗 |
| `clients` | array | 客户 Tab |
| `projects` | array | 项目卡片、工作室、Pipeline |
| `tasks` | array | 角色弹窗任务 |
| `hitlQueue` | array | HITL 审批 |
| `alerts` | array | 脉搏告警横幅 |
| `channels` | object | CEO 办公室、设置 |
| `artifacts` | array | 工作室列表与预览 |
| `inbox` | array | 收件箱 |
| `rejectHistory` | array | 驳回历史 |
| `closure` | object | 结项清单（key=projectId） |
| `payments` | array | 客户详情收款 |
| `weeklyReport` | object | 周报 Tab |
| `rolePerformance` | array | 周报角色表现 |
| `ceoThread` | array | CEO FAB |
| `costs` | object | 经营 Tab |
| `roleConfig` | array | 设置 |

**完整字段样例以 Mock 文件为准**；增字段可以，**删/改名不行**（除非同步改前端 + 本文档版本号）。

---

## 9. 前端 → API 映射表

| 前端函数 | 当前 Mock 行为 | 目标 API |
|----------|----------------|----------|
| `init()` | `fetch(dashboard.json)` | `GET /api/v1/dashboard` |
| `openInboxItem` → 已读 | `item.read = true` | `PATCH /inbox/{id}` `{ "read": true }` |
| `resolveRequest` | 本地改 status | `POST /inbox/{id}/resolve` |
| `approveHitl` | 本地多表更新 | `POST /hitl/{id}/approve` |
| `rejectHitl` | 本地 rejectHistory | `POST /hitl/{id}/reject` |
| `submitBrief` | push ceoThread | `POST /ceo/brief` |
| `sendWeeklyMock` | 改 weeklyReport.status | `POST /weekly/current/send` |
| `exportProjectZip` | 客户端 JSZip | `GET /projects/{id}/export?type=internal` |
| `exportClientDeliveryZip` | 客户端 JSZip | `GET /projects/{id}/export?type=client` |
| `exportWeeklyMd/Pdf` | 客户端生成 | `GET /weekly/current/export?format=` |
| `showRoleConfig` / 设置 | 读 roleConfig | `GET /roles/config` |
| （Phase 2e）保存 Key | 无 | `PUT /roles/config/{roleId}` |

---

## 10. 契约测试（保证一次性过）

### 10.1 黄金文件测试

```python
# backend/tests/test_dashboard_contract.py
def test_dashboard_matches_schema(client):
    r = client.get("/api/v1/dashboard")
    data = r.json()["data"]
    assert set(data.keys()) == set(GOLDEN_TOP_LEVEL_KEYS)
    # 可选：jsonschema.validate(data, load_schema("dashboard"))
```

**黄金文件：** 启动时用 `mock/dashboard.json` 种子灌库，API 输出与之一致（允许 `updatedAt` 等动态字段）。

### 10.2 状态机测试

每个 §6 写操作至少 **1 个集成测试**：调用 API → 断言 DB + 响应 patch + 再 GET dashboard 字段。

### 10.3 前端冒烟

```bash
# Phase 2a 完成后
OPC_API=1 ./start.sh
# 浏览器走一遍：概览→项目→收件箱→批准HITL→经营→周报
```

### 10.4 文档同步规则

| 变更类型 | 必须更新 |
|----------|----------|
| 新增字段 | `mock/dashboard.json` + 本文档 §8 |
| 新增写操作 | 本文档 §5 + §6 + §9 |
| 枚举变更 | 本文档 §4 |
| 破坏性变更 | 版本升至 v2，前后端同 PR |

---

## 11. 前端接入方式（Phase 2a）

```javascript
// dashboards/app/js/api.js（建议新建）
const API_BASE = `${window.location.origin}/api/v1`;

async function loadDashboard() {
  const res = await fetch(`${API_BASE}/dashboard`);
  const json = await res.json();
  if (!json.ok) throw new Error(json.error?.message);
  return json.data;  // 形状与 mock/dashboard.json 相同
}

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}
```

`app.js` 中 Mock 写操作逐步改为 `apiPost`，成功后 `Object.assign(data, patch)` 或 `data = await loadDashboard()`。

---

## 12. OpenAPI

Phase 2a 完成后，FastAPI 自动生成：

```
http://127.0.0.1:8765/docs
```

本文档为 **业务契约**；OpenAPI 为 **机器可读补充**。冲突时以本文档 + Mock JSON 为准。

---

## 13. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-05 | 对齐前端 Mock v0.3.0，覆盖全部 Tab 与写操作 |
