# OPC Studio · 完整开发计划

| 项 | 内容 |
|----|------|
| 版本 | **v2.0** |
| 状态 | **Phase 2a–2c/2e Done · Phase 3 骨架 Done · 2d/4 未做** · [DEV-STATUS.md](./DEV-STATUS.md) |
| 范围 | Phase 1（已完成）→ Phase 4（可选上云）全链路 |
| 关联 | [PRD.md](./PRD.md) · [BACKEND.md](./BACKEND.md) · [API.md](./API.md) · [AGENTS.md](./AGENTS.md) · [DEV-STATUS.md](./DEV-STATUS.md) |
| 前端基线 | Mock v0.3 · `dashboards/app/` |
| 契约基准 | `mock/dashboard.json` |

---

## 0. 本文档做什么

**一份文档覆盖全部开发节奏**，替代原先仅 Phase 2 后端的子计划。

| 阶段 | 交付物 | 你得到什么 |
|------|--------|------------|
| **Phase 1** ✅ | Mock 看板 | UX 验证完成 |
| **Phase 2** | 控制面 API + DB + 文件 | 持久化台账、HITL、结项、周报——**智能工作流 UI** |
| **Phase 3** | Orchestrator + Role Runners | **真正的 Agent 公司**：CEO 派活、Handoff、LLM 产出 |
| **Phase 4** | 飞书深度集成 · 可选上云 | 渠道 Ingress、远程访问 |

**Phase 2 与 Phase 3 的关系：**

```
Phase 2 = 控制面（台账 + 状态机 + 文件）
Phase 3 = 编排层 + 执行层（生产 Phase 2 里展示的数据）
```

Phase 2 **必须**为 Phase 3 预留表结构与 Orchestrator Hook；Phase 3 **不**重写前端，只替换「数据从哪来」。

---

## 1. 技术共识（全局）

| 项 | 决策 |
|----|------|
| 框架 | FastAPI + uvicorn |
| 数据库 | SQLite `data/opc.db`（WAL） |
| 文件 | `data/projects/{projectId}/artifacts/` · `deliveries/` |
| 部署 | 本地 `./start.sh`，绑定 `127.0.0.1:8765` |
| 认证 | 无（单用户本地） |
| ORM | **SQLModel** |
| API 前缀 | `/api/v1` |
| 响应格式 | `{ ok, data }` / `{ ok, error }` |
| Agent 协作 | CEO 星型 + Handoff；**例外** CEO 会诊室（AGENTS §4.1） |
| 工作流引擎 | Phase 3a 自研转移表；LangGraph 备选 |
| 渠道 | 飞书 Phase 2d/4；微信后置 |
| 明确不做 | Docker 必选 · 登录 · 多租户 · Agent 自由群聊 |

---

## 2. 里程碑总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 1  ✅ Mock 看板 v0.3                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2  控制面（约 3–4 周兼职）                                              │
│   2a 骨架 + dashboard 只读          ← 编码起点                                 │
│   2b 项目文件 + 工作室                                                        │
│   2c 写操作 + 状态机 + Orchestrator Hook 占位                                  │
│   2e 角色配置加密                                                             │
│   2d 飞书 Webhook（可选，可放到 Phase 4）                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 3  Agent 编排与执行（约 5–7 周兼职）★ 产品分水岭                          │
│   3a 编排骨架 + 转移表                                                        │
│   3b CEO Runner（Brief → Dispatch）                                          │
│   3c 四角色 Runners + Handoff 链                                              │
│   3d 工具白名单 + agent_runs 成本                                             │
│   3e PoC 分支 + 多项目并行                                                    │
│   3f CEO 会诊室（Deliberate）                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 4  渠道与部署（约 1–2 周，按需）                                          │
│   4a 飞书 Ingress 深度集成                                                    │
│   4b SSE 实时推送完善                                                         │
│   4c 可选上云（systemd + HTTPS）                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**推荐执行顺序：** `2a → 2b → 2c → 2e → 3a → 3b → 3c → 3d → 3e/3f（可并行）→ 2d/4a`

**每阶段 Done 定义：** 本节末尾验收清单 **全部打勾** 才进入下一阶段。

---

## 3. Phase 1 · Mock 看板 ✅

**状态：已完成**

| 交付 | 路径 |
|------|------|
| 静态看板 7 Tab + CEO FAB | `dashboards/app/` |
| 黄金样本 JSON | `mock/dashboard.json` v0.3.0 |
| 业务全景 | `architecture.html` |
| JSON Schema | `schemas/dashboard.v1.schema.json` |

**已验证：** 五角色脉搏、项目工作室、收件箱 HITL、经营盈亏、周报、结项 ZIP 演示路径。

**Phase 2 不重写 UI**，只改数据入口与写操作 API。

---

## 4. Phase 2 · 控制面

### 4.0 Phase 2 目标

在 **不重写前端布局** 的前提下，用 FastAPI + SQLite + 本地文件替换 Mock JSON。

**成功标准（Phase 2 整体 Done）：**

- `./start.sh` 一键启动，功能与 Mock 阶段 **等价**
- 所有写操作走后端 API，刷新/重开页面 **状态持久化**
- 产出物按项目存入 `data/projects/{id}/artifacts/`
- 契约测试 CI 通过
- 编排预留表已建，写 API 已接 **Orchestrator Hook 占位**

**Phase 2 完成后仍缺什么（2026-05 更新）：** Phase 3 已接 Orchestrator + Runners；**无 Key 时 Stub**，配 Key 可走 LLM。仍缺：飞书全链路、`GET /events` SSE、写 API patch 响应。

---

### 4.1 Phase 2a · 骨架 + 只读 Dashboard

**周期：** 约 5–7 天（兼职）

**目标：** 关掉 `python -m http.server`；后端提供 Mock 等价数据；前端只改数据入口。

#### 任务清单

| # | 任务 | 产出 | 依赖 |
|---|------|------|------|
| 2a-1 | 初始化 `backend/pyproject.toml` | fastapi, uvicorn, sqlmodel, cryptography, httpx, pytest | — |
| 2a-2 | `app/config.py` | `OPC_DATA_DIR`, `OPC_HOST`, `OPC_PORT`, `OPC_SECRET_KEY` | 2a-1 |
| 2a-3 | `app/db.py` | SQLite 引擎、`create_all`、WAL | 2a-2 |
| 2a-4 | **全量建表**（见 §8） | `models/*.py` | 2a-3 |
| 2a-5 | `app/seed.py` | 读 `mock/dashboard.json` → DB + 拷贝 artifacts | 2a-4 |
| 2a-6 | `services/dashboard.py` | DB 聚合 → Dashboard JSON（camelCase） | 2a-5 |
| 2a-7 | `GET /api/v1/dashboard` | `{ ok: true, data: {...} }` | 2a-6 |
| 2a-8 | `GET /api/v1/health` | 健康检查 | 2a-1 |
| 2a-9 | `main.py` 静态挂载 | `/` → `dashboards/app/` | 2a-7 |
| 2a-10 | 契约测试 | 顶层键与 Mock 一致；jsonschema 可选 | 2a-7 |
| 2a-11 | 更新 `start.sh` | uvicorn 启动 | 2a-9 |
| 2a-12 | 前端 `api.js` + `init()` | `fetch('/api/v1/dashboard')` | 2a-11 |
| 2a-13 | `services/orchestrator_hooks.py` | **空占位** + 文档注释 | 2a-4 |
| 2a-14 | 灌 `workflow_templates` | Acme 默认 5 阶段转移表 JSON（只读 seed） | 2a-5 |

#### 验收（2a Done）

- [x] `./start.sh` → 看板视觉与 Mock 一致
- [x] Network：`/api/v1/dashboard`，非 `mock/dashboard.json`
- [x] `pytest backend/tests` 全绿
- [x] 删 `data/` 重启，seed 自动重建
- [x] OpenAPI：`http://127.0.0.1:8765/docs`
- [x] 编排预留表存在（可空）：`agent_runs`, `handoffs`, `orchestration_events`, `deliberation_*`, `workflow_templates`

#### 前端改动（2a）

| 文件 | 改动 |
|------|------|
| `dashboards/app/js/api.js` | 新建 `loadDashboard()` |
| `dashboards/app/js/app.js` | `init()` 改 API；写操作仍本地 Mock |
| `dashboards/app/index.html` | 引入 `api.js` |

#### 决策（2a 默认）

| # | 问题 | 默认 |
|---|------|------|
| D1 | 2c refresh 策略 | **全量 `loadDashboard()`**（简单优先） |
| D2 | artifacts 正文 | 2a 全量进 JSON；2b 再懒加载 `/content` |
| D3 | ORM | SQLModel |

---

### 4.2 Phase 2b · 项目存储 + 工作室

**周期：** 约 4–5 天

**目标：** 产出物正文走文件系统；工作室预览/导出走后端。

#### 任务清单

| # | 任务 | API | 依赖 |
|---|------|-----|------|
| 2b-1 | `services/project_store.py` | 原子写、hash | 2a |
| 2b-2 | 产出物 CRUD | `GET/POST/PUT .../artifacts` | 2b-1 |
| 2b-3 | 产出物正文 | `GET/PUT .../artifacts/{id}/content` | 2b-1 |
| 2b-4 | 项目详情 | `GET /projects/{id}` | 2a |
| 2b-5 | 客户 API | `GET /clients`, `GET /clients/{id}` | 2a |
| 2b-6 | 前端工作室 | 懒加载 content（可选） | 2b-3 |
| 2b-7 | 集成测试 | 写 md → 重启 → 读回一致 | 2b-3 |

#### 验收（2b Done）

- [x] 工作室正文来自 API/文件
- [x] `data/projects/proj-acme/artifacts/` 有真实文件
- [x] 客户 Tab 可走独立 API（或与 dashboard 重复无妨）

---

### 4.3 Phase 2c · 写操作 + 状态机

**周期：** 约 7–10 天

**目标：** 前端全部 Mock 写操作改 API；实现 [API.md §6](./API.md) 副作用与衍生字段重算。

#### 写接口实施顺序

| 顺序 | 接口 | 前端函数 | 状态机 |
|------|------|----------|--------|
| 1 | `PATCH /inbox/{id}` | 已读 | 简单 |
| 2 | `POST /inbox/{id}/resolve` | `resolveRequest` | §6.3 |
| 3 | `POST /hitl/{id}/approve` | `approveHitl` | §6.1 ★ |
| 4 | `POST /hitl/{id}/reject` | `rejectHitl` | §6.2 |
| 5 | `POST /ceo/brief` | `submitBrief` | §6.6（Phase 2：固定 ack + 存消息） |
| 6 | `POST /weekly/current/send` | `sendWeeklyMock` | §6.5 |
| 7 | `GET /projects/{id}/export` | ZIP 导出 | §6.4 |

#### 后端模块

```
services/
├── aggregates.py          # recompute_pulse / stats / finance / role_counts
├── state_machines.py      # HITL / closure / inbox 转移
├── export_service.py      # 客户 ZIP
└── orchestrator_hooks.py  # 每个写 API 末尾调用 hook（Phase 3 替换实现）
```

**Hook 约定（Phase 2c 必做）：**

```python
# 例：HITL 批准后
await orchestrator_hooks.on_hitl_approved(hitl_id, project_id)  # Phase 2: pass
                                                                # Phase 3: Orchestrator.on_event
```

#### 衍生字段（每个写接口后）

- `recompute_pulse()` · `recompute_stats()` · `recompute_role_counts()` · `recompute_finance_by_project()`

写成功后前端 **全量 refresh**（首版策略）。

#### 可选（2c 末期）

| # | 任务 | API |
|---|------|-----|
| 2c-opt-1 | SSE 推送 | `GET /api/v1/events` |
| 2c-opt-2 | patch 响应 | 减少 refresh 流量 |

#### 验收（2c Done）

- [x] 全路径：**HITL-3 批准 → 结项清单 → 客户 ZIP → 发周报**
- [x] 刷新后状态保持
- [x] 每个写接口 ≥1 集成测试
- [x] `pulse` / `stats` / `costs.byProject` 与操作后一致
- [x] `orchestrator_hooks` 已被所有写 API 调用（Phase 3 已替换真实实现）

> **未完成（2c-opt）：** `GET /events` SSE · 写 API 返回 DashboardPatch — 见 [DEV-STATUS.md §3.5](./DEV-STATUS.md#35-p2--体验--上云)

#### 前端改动（2c）

| 函数 | 改为 |
|------|------|
| `approveHitl` / `rejectHitl` | POST + refresh |
| `resolveRequest` | POST + refresh |
| `submitBrief` | POST + refresh |
| `sendWeeklyMock` | POST + refresh |
| `exportProjectZip` 等 | GET blob 下载 |
| `openInboxItem` 已读 | PATCH |

---

### 4.4 Phase 2e · 角色配置

**周期：** 约 2–3 天

| # | 任务 | 说明 |
|---|------|------|
| 2e-1 | `security/secrets.py` | Fernet + `OPC_SECRET_KEY` |
| 2e-2 | `GET/PUT /roles/config/{roleId}` | Key 打码 |
| 2e-3 | `.env.example` | SECRET_KEY 生成说明 |
| 2e-4 | 前端设置页表单 | 保存调 PUT |

#### 验收（2e Done）

- [x] DB 无明文 api_key
- [x] GET 永不返回完整 Key
- [x] 重启后配置仍在
- [x] `POST /roles/{id}/avatar` 头像持久化（扩展）

---

### 4.5 Phase 2d · 飞书 Webhook（可选 · 可延后到 Phase 4a）

**前置：** 公网 URL（ngrok 或域名）

| # | 任务 |
|---|------|
| 2d-1 | `channels/base.py` |
| 2d-2 | `channels/feishu.py` 验签 |
| 2d-3 | `POST /channels/feishu/webhook` |
| 2d-4 | `ceo_router.ingest()` → `ceo_messages` + inbox |
| 2d-5 | `channel_config` CRUD |
| 2d-6 | 飞书出站回复 |

#### 验收（2d Done）

- [ ] 飞书发消息 → Web CEO 线程可见

> **现状：** `POST /channels/feishu/webhook` 返回 **501**；inbound 统一入口与 ClawBot 指引已上线 — [CHANNELS-INTEGRATION.md](./CHANNELS-INTEGRATION.md)

---

### 4.6 Phase 2 联调检查表

| Tab | 只读 | 写操作 | 阶段 |
|-----|------|--------|------|
| 概览 | 脉搏、角色 | — | 2a |
| 项目 | 卡片 | — | 2a |
| 工作室 | 预览 MD | 导出 ZIP | 2b/2c |
| 客户 | 档案 | — | 2b |
| 收件箱 | 列表 | 已读、请示、HITL | 2c |
| 经营 | P&L | — | 2a |
| 周报 | 一页纸 | 发送 | 2c |
| CEO FAB | 线程 | 投递简报 | 2c |
| 设置 | 角色配置 | 保存 Key | 2e |

---

## 5. Phase 3 · Agent 编排与执行

> **Phase 2 Done 后仍是「智能工作流 UI」；Phase 3 才是 Agent 公司。**  
> 设计详见 [AGENTS.md](./AGENTS.md)。

### 5.0 Phase 3 目标

| 能力 | 说明 |
|------|------|
| Orchestrator | 事件驱动：Dispatch / Handoff / HITL / Complete |
| CEO Runner | Brief 解析 → 立项判断 → 派 Task |
| Role Runners | 四角色 LLM 执行 → 写 artifact → Handoff |
| 成本 | `agent_runs` 实时计入经营页 |
| 会诊室 | 模糊需求时 CEO 开室，Founder 旁观（§4.1） |

**成功标准（Phase 3 整体 Done）：**

- 投递一条 Acme 类 Brief → **无需手动改 DB**，task 链自动推进至 HITL-3
- `POST /ceo/brief` 不再是固定 ack
- `POST /hitl/{id}/approve` 内部走 Orchestrator，自动 Dispatch 下游
- 经营页 Token 成本随 `agent_runs` 更新
- 至少一条 **会诊室** 路径可演示：开室 → turns → Decision Memo → 关室 → Dispatch

---

### 5.1 Phase 3a · 编排骨架

**周期：** 约 7–10 天  
**依赖：** Phase 2a–2c Done

#### 任务清单

| # | 任务 | 产出 |
|---|------|------|
| 3a-1 | `orchestrator/events.py` | `OrcheEvent` 类型枚举 |
| 3a-2 | `orchestrator/engine.py` | `Orchestrator.on_event()` 主循环 |
| 3a-3 | `orchestrator/transitions.py` | 读 `workflow_templates` 转移表 |
| 3a-4 | `orchestrator/dispatcher.py` | `dispatch_task(role, task_spec)` |
| 3a-5 | `orchestrator/router.py` | `route_handoff()` · 依赖检查 |
| 3a-6 | `services/workflow_state.py` | `project.workflow_state`: active / deliberating / waiting_hitl |
| 3a-7 | 写 `orchestration_events` | 每个 event append-only 日志 |
| 3a-8 | 替换 `orchestrator_hooks.py` | 写 API → 真实 `on_event()` |
| 3a-9 | **Stub Runners** | 不调用 LLM，只改 task 状态 + 假 Handoff（验证链） |
| 3a-10 | CLI / 测试触发器 | `pytest` 或 `scripts/trigger_event.py` 手动发 event |
| 3a-11 | Acme 转移表 seed | 5 阶段 + PoC 分支 YAML/JSON 入库 |

#### 协作原语（实现顺序）

1. `Dispatch` → 2. `Handoff` → 3. `Complete` → 4. `Wait` → 5. `HITL Request` → 6. `Escalate` → 7. `Deliberate`（3f）

#### 验收（3a Done）

- [x] 手动 `Handoff(dev→ceo)` → Orchestrator 自动创建 HITL-3 inbox
- [x] 手动 `HITLApproved` → 自动 Dispatch ops 结项 task
- [x] `orchestration_events` 可重放整条链
- [x] `workflow_state=deliberating` 时拒绝并行 Dispatch（为 3f 预留）

---

### 5.2 Phase 3b · CEO Runner

**周期：** 约 7–10 天  
**依赖：** 3a + 2e（角色配置可读）

#### 任务清单

| # | 任务 | 产出 |
|---|------|------|
| 3b-1 | `runners/base.py` | `RoleRunner` 抽象 |
| 3b-2 | `runners/ceo.py` | CEO Runner |
| 3b-3 | `prompts/ceo/` | system prompt + charter |
| 3b-4 | Brief 结构化输出 | JSON schema：`client`, `scope`, `budget`, `risk` |
| 3b-5 | `InboundBrief` 事件 | `POST /ceo/brief` → Orchestrator |
| 3b-6 | 立项评估 | assess → 不接 / 澄清 / 立项 / PoC |
| 3b-7 | Dispatcher 逻辑 | 决定 Dispatch 哪个角色 |
| 3b-8 | HITL 打包 | CEO 汇总 artifact → `hitl_queue` |
| 3b-9 | `agent_runs` 首版写入 | CEO 调用记 tokens |
| 3b-10 | 后台任务队列 | `BackgroundTasks` 或 `asyncio.Queue` 跑 Runner |
| 3b-11 | 前端 CEO FAB | 显示「评估中…」→ SSE/轮询 task 更新 |

#### 验收（3b Done）

- [x] Web 投递模糊 Brief → 自动创建 CEO 评估 task + inbox 条目（Stub/LLM）
- [x] 评估完成 → artifact `art-memo-*` 写入文件
- [x] 你批 PoC/立项 → Orchestrator 自动 Dispatch 下游（接 3a 链）
- [x] CEO Runner 使用 `role_config` 中的 api_url / key

---

### 5.3 Phase 3c · 四角色 Runners

**周期：** 约 10–14 天  
**依赖：** 3b

#### 任务清单

| # | 角色 | 典型 Task | 产出 artifact |
|---|------|-----------|---------------|
| 3c-1 | product | PRD | `art-prd-*.md` |
| 3c-2 | legal | 报价/SOW | `art-sow-*.md` |
| 3c-3 | dev | Demo / 交付 | `art-demo-*.md` · staging 说明 |
| 3c-4 | ops | 验收清单 · 客户邮件 | `art-acceptance-*.md` |
| 3c-5 | 共用 | `runners/{role}.py` + prompts | 结构化输出解析 |
| 3c-6 | Handoff 链 | product→legal→dev→ops | `handoffs` 表完整 |
| 3c-7 | 活动流 | `task_activities` 自动写入 | 角色详情 Tab |
| 3c-8 | 失败重试 | Runner failed → Escalate CEO | inbox 必读 |

#### Handoff 链（Acme 验收路径）

```
CEO assess
  → product PRD → HITL-1（你批）
  → legal SOW → HITL-2（你批）
  → dev Demo/PoC → dev 交付 → HITL-3（你批）
  → ops 结项清单 → HITL-4（你批）
  → closure ZIP
```

#### 验收（3c Done）

- [x] **零手动改 DB**，从 Brief 到 HITL-3 可跑通（Stub LLM fixture 测编排）
- [x] 各 artifact 在工作室可见
- [x] Handoff 触发下一角色 task 自动 `running`
- [x] 驳回 HITL → `rework_or_escalate` 创建返工 task

---

### 5.4 Phase 3d · 工具与成本

**周期：** 约 5–7 天  
**依赖：** 3c

#### 任务清单

| # | 任务 | 说明 |
|---|------|------|
| 3d-1 | `role_config.tools` 白名单 | JSON 列表 per role |
| 3d-2 | `tools/registry.py` | 注册可调用工具 |
| 3d-3 | ops：`update_pipeline` | 写 Pipeline 列 |
| 3d-4 | dev：`write_artifact_file` | 写 md 到 project_store |
| 3d-5 | legal：`read_template` | 读合同模板 |
| 3d-6 | LLM tool-calling 循环 | 限制 max steps |
| 3d-7 | `agent_runs` 完整 | tokens_in/out, cost_cny, model |
| 3d-8 | `token_runs` 聚合 | 写入 dashboard `costs` |
| 3d-9 | 经营页联动 | `recompute_finance_by_project` 含 LLM 成本 |

#### 验收（3d Done）

- [x] 每次 LLM 调用有 `agent_runs` 记录
- [x] 经营 Tab「项目盈亏」含 Token 成本
- [ ] 超预算 → CEO Escalate 进 inbox（当前仅经营页 `budgetAlert`，无 inbox 升级）

---

### 5.5 Phase 3e · PoC 分支 + 多项目并行

**周期：** 约 5–7 天  
**依赖：** 3c

#### 任务清单

| # | 任务 | 说明 |
|---|------|------|
| 3e-1 | 转移表 PoC 分支 | assess → poc_demo → 回流 assess/签约 |
| 3e-2 | Beta 项目 seed | 第二条并行项目线 |
| 3e-3 | 项目级锁 | 同项目串行、跨项目并行 |
| 3e-4 | Runner 队列 | 多 `agent_runs` 不互相踩 SQLite |
| 3e-5 | 脉搏聚合 | 两项目同时 running 时 UI 正确 |

#### 验收（3e Done）

- [x] Acme + Beta 同时跑，task/handoff 不串项目
- [ ] PoC 分支：Brief → PoC Demo → 回流立项 可演示（转移表有；E2E 演示未固化）

---

### 5.6 Phase 3f · CEO 会诊室

**周期：** 约 5–7 天  
**依赖：** 3a–3c（可与 3e 并行）

#### 任务清单

| # | 任务 | 产出 |
|---|------|------|
| 3f-1 | `orchestrator/deliberation.py` | `open` / `run_round` / `close` |
| 3f-2 | `Deliberate` 事件 | 写入 `deliberation_sessions` / `turns` |
| 3f-3 | 触发白名单 | Brief 模糊 · assess→clarify · scope 冲突 |
| 3f-4 | 轮次上限 | max_rounds=2, max_roles=3 |
| 3f-5 | CEO 主持顺序调用 | 禁止 Agent 互聊 API |
| 3f-6 | Decision Memo | artifact `art-decision-*` |
| 3f-7 | 关室收口 | Dispatch 或 HITL |
| 3f-8 | API | `GET /projects/{id}/deliberation` |
| 3f-9 | API | `POST .../deliberation/{sid}/founder-note`（旁观插话） |
| 3f-10 | 前端会诊抽屉 | 只读 turns + Memo 链接 |
| 3f-11 | SSE | `deliberation.opened` / `turn.recorded` / `closed` |

#### 验收（3f Done）

- [x] 投递极模糊 Brief → CEO 开室（非直接 Dispatch）
- [ ] Founder 在看板旁观 turns，可不插话（API 有；**专用 UI 缺**）
- [x] 关室后产生 Decision Memo + 正式 task 链恢复
- [x] 会诊期间其他 Dispatch 被阻塞

---

### 5.7 Phase 3 后端目录（目标结构）

```
backend/app/
├── orchestrator/
│   ├── engine.py
│   ├── events.py
│   ├── transitions.py
│   ├── dispatcher.py
│   ├── router.py
│   └── deliberation.py          # 3f
├── runners/
│   ├── base.py
│   ├── ceo.py
│   ├── product.py
│   ├── legal.py
│   ├── dev.py
│   └── ops.py
├── prompts/
│   ├── ceo/ · product/ · ...
├── tools/
│   ├── registry.py
│   └── ...
├── channels/                      # 2d/4a
│   ├── base.py
│   └── feishu.py
└── services/
    ├── orchestrator_hooks.py    # → orchestrator.engine
    └── ...
```

---

## 6. Phase 4 · 渠道与可选上云

**周期：** 按需，约 1–2 周

### 6.1 Phase 4a · 飞书 Ingress 深度集成

| # | 任务 |
|---|------|
| 4a-1 | 飞书消息 → `InboundBrief`（与 Web 同入口） |
| 4a-2 | HITL 通知 → 飞书卡片（可选一键批/驳链接回 Web） |
| 4a-3 | CEO 回复 → 飞书 outbound |
| 4a-4 | `channel_config` 设置页 UI |

### 6.2 Phase 4b · 实时体验

| # | 任务 |
|---|------|
| 4b-1 | SSE 全覆盖：task / inbox / handoff / deliberation |
| 4b-2 | 前端去轮询，改 EventSource |
| 4b-3 | CEO FAB / 角色详情实时刷新 |

### 6.3 Phase 4c · 可选上云

| # | 任务 |
|---|------|
| 4c-1 | systemd unit + 日志轮转 |
| 4c-2 | Caddy HTTPS 反向代理 |
| 4c-3 | `data/` 备份脚本 + 文档 |
| 4c-4 | 简单访问控制（Basic Auth 或 Tailscale，仍非多用户产品） |

**仍不做：** 多租户 SaaS · 强制 Docker

---

## 7. 仓库结构演进

### 7.1 Phase 2a 完成后

```
opc-agent-framework/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py · db.py · seed.py
│   │   ├── models/ · schemas/
│   │   ├── services/
│   │   └── api/
│   └── tests/
├── dashboards/app/          # 现有前端
├── mock/dashboard.json      # 契约黄金样本（保留）
├── data/                    # gitignore
├── start.sh
├── .env.example
└── docs/
```

### 7.2 Phase 3 完成后（增量）

```
backend/app/
├── orchestrator/            # §5.7
├── runners/
├── prompts/
├── tools/
└── channels/
```

---

## 8. 数据库与 API 全景

### 8.1 表清单（Phase 2a 一次建齐）

| 表 | Phase 2 | Phase 3 |
|----|---------|---------|
| `projects` · `clients` · `tasks` · `artifacts` | 读写 | 读写 |
| `inbox_items` · `hitl_queue` · `closure_checklists` | 读写 | Orchestrator 写 |
| `ceo_messages` · `weekly_reports` · `finance_snapshots` | 读写 | 读写 |
| `role_config` · `channel_config` | 2e/2d | 3b+ |
| `agent_runs` · `handoffs` · `orchestration_events` | 空表 | 3a+ 写入 |
| `deliberation_sessions` · `deliberation_turns` | 空表 | 3f 写入 |
| `workflow_templates` | seed | 3a 读 |

完整字段见 [BACKEND.md §4](./BACKEND.md) 与 [AGENTS.md §7](./AGENTS.md)。

### 8.2 API 全景

| 类别 | 文档 | Phase |
|------|------|-------|
| 读聚合 | `GET /dashboard` | 2a |
| 项目/产出物 | `/projects/*` · `/artifacts/*` | 2b |
| 写操作 | `/hitl/*` · `/inbox/*` · `/ceo/brief` · `/weekly/*` | 2c |
| 角色配置 | `/roles/config/*` | 2e |
| 飞书 | `/channels/feishu/*` | 2d/4a |
| SSE | `/events` | 2c opt / 4b |
| 会诊 | `/projects/{id}/deliberation/*` | 3f |

契约细节：[API.md](./API.md)（Phase 3 新增接口需同步增补 API.md v1.1）。

---

## 9. 测试与质量门禁

### 9.1 三层测试

| 层 | 内容 | 阶段 |
|----|------|------|
| L1 契约 | dashboard 顶层键、枚举 | 2a 起 |
| L2 集成 | 写操作 → GET dashboard | 2c 起 |
| L3 编排 | event 链 → task 状态 | 3a 起 |
| L4 Runner | mock LLM → artifact 文件 | 3c 起 |
| L5 冒烟 | 浏览器手动路径 | 每阶段 Done |

### 9.2 必测用例

```
# Phase 2
test_dashboard_top_level_keys
test_hitl_approve_updates_closure_and_pulse
test_hitl_reject_appends_reject_history
test_export_client_zip_valid
test_role_config_masks_api_key

# Phase 3
test_handoff_triggers_next_dispatch
test_hitl_approved_via_orchestrator_dispatches_ops
test_ceo_brief_creates_assessment_task
test_deliberation_blocks_parallel_dispatch
test_deliberation_close_produces_decision_memo
test_two_projects_no_cross_contamination
```

### 9.3 本地命令

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

### 9.4 阶段门禁

| 门禁 | 条件 |
|------|------|
| 进入 2b | 2a 验收全勾 |
| 进入 2c | 2b 验收全勾 |
| 进入 3a | 2c + 2e 验收全勾 |
| 进入 3b | 3a 验收全勾 |
| 发布「可用 Agent 公司」 | 3c Done + 至少 3d 成本记账 |

---

## 10. 风险与缓解

| 风险 | 阶段 | 缓解 |
|------|------|------|
| 前后端字段不一致 | 2a | Mock JSON = 契约；jsonschema 测试 |
| 2c 状态机与 Mock 行为分叉 | 2c | 对照 API.md §6 逐条集成测试 |
| Phase 3 推倒 2c 副作用 | 2c | **Orchestrator Hook** 统一入口 |
| LLM 输出不可解析 | 3b–3c | JSON mode + 重试 + fallback Escalate |
| Token 成本失控 | 3d/3f | agent_runs 预算 + 会诊轮次上限 |
| SQLite 写并发 | 3e | 单 worker + 项目级队列 |
| 会诊变自由群聊 | 3f | CEO 顺序调用、禁止 Agent 直连（AGENTS §4.1） |
| 飞书验签/网络 | 2d/4a | 本地 ngrok 先测；失败降级仅 Web |

---

## 11. 工时估算

**假设：单人兼职，每周有效开发 15–20 小时**

| 阶段 | 子阶段 | 预估 |
|------|--------|------|
| Phase 2 | 2a + 2b + 2c + 2e | **3–4 周** |
| Phase 2 | 2d 飞书（可选） | +3–5 天 |
| Phase 3 | 3a + 3b + 3c | **4–5 周** |
| Phase 3 | 3d + 3e + 3f | **2–3 周** |
| Phase 4 | 4a–4c 按需 | **1–2 周** |
| **合计（至可演示 Agent 公司）** | 2 + 3a–3d | **约 8–12 周** |
| **合计（含会诊 + 飞书 + 上云）** | 全量 | **约 10–14 周** |

集中全职可压缩约 **40–50%**。

---

## 12. 数据迁移与备份

| 操作 | 方式 |
|------|------|
| 首次启动 | 自动 seed |
| 重置样例 | 删 `data/` → 重启 |
| 备份 | 复制整个 `data/` |
| Schema 升级 | `schema_version` + 增量 SQL |
| Phase 2 → 3 | 不删库；编排表从空变为有数据 |

---

## 13. Founder 确认项

请逐项确认或标注修改意见：

| # | 确认项 | 默认建议 | 你的意见 |
|---|--------|----------|----------|
| 1 | 本计划 v2.0 覆盖 Phase 1–4 | 同意作为唯一实施主文档 | ☐ |
| 2 | 编码起点：**Phase 2a** | 同意 | ☐ |
| 3 | 顺序：2a→2b→2c→2e→3a→3b→3c→3d→3e/3f | 同意 | ☐ |
| 4 | 2c 写操作后 **全量 refresh** | 先简单 | ☐ |
| 5 | SQLModel + 2a 一次建齐所有表 | 同意 | ☐ |
| 6 | 2d 飞书可延后到 Phase 4a | 同意 | ☐ |
| 7 | Phase 3 工作流：自研转移表 | 同意 | ☐ |
| 8 | CEO 星型 + Handoff + 例外会诊室 | 同意 | ☐ |
| 9 | 工时 8–12 周（兼职至 Agent 公司可演示） | 可接受 / 要压缩 | ☐ |
| 10 | 确认后开始 Phase 2a 编码 | — | ☐ |

**确认后下一步：**

1. 初始化 `backend/` 骨架  
2. 契约测试 + `api.js`  
3. 更新 `start.sh`

---

## 14. 文档索引

| 文档 | 职责 |
|------|------|
| [PRD.md](./PRD.md) | 做什么、场景 |
| [BACKEND.md](./BACKEND.md) | 架构与技术选型 |
| [API.md](./API.md) | 接口契约与状态机 |
| [AGENTS.md](./AGENTS.md) | Agent 编排、会诊室、原语 |
| [AGENTS-COMPARE.md](./AGENTS-COMPARE.md) | 编排模式对比 |
| **IMPLEMENTATION.md（本文）** | **全链路开发计划与验收** |
| `mock/dashboard.json` | 契约黄金样本 |

---

## 15. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-05 | Phase 2 后端子计划 |
| **v2.0** | 2026-05 | **扩展为 Phase 1–4 完整开发计划；细化 Phase 3a–3f 任务与验收** |
