# Pulse + Agency 运行时规格（v1）

| 项 | 内容 |
|----|------|
| 版本 | **v1.0-draft** |
| 状态 | **v1.1 · Phase B 已实现** |
| 关联 | [CEO-ORCHESTRATION-ROADMAP.md](./CEO-ORCHESTRATION-ROADMAP.md) · [IMPLEMENTATION.md](./IMPLEMENTATION.md) · [API.md](./API.md) |
| 代码基线 | OPC Studio **v0.9.0** |

---

## 1. 要解决什么

当前问题不是「缺某个 UI 刷新」，而是 **执行与自主行为没有统一调度**：

| 现状 | 后果 |
|------|------|
| 任务执行绑在 HTTP `BackgroundTasks` | 重启丢 workflow；无断点续跑 |
| `dispatch_task` 创建即 `running` | 中断后僵尸任务 |
| `handoffs` 表只写不消费 | 角色交接链断裂 |
| 前端 2s 全量 `GET /dashboard` | 浪费带宽；与执行无关 |
| `run_scheduler_tick` 仅 commitment 提醒 | 不执行任务、不驱动 CEO/角色自主观察 |
| `workflow_engine.get_next_steps` 孤立存在 |  proactive cue 未进入统一管道 |

**目标：** 一个 **Pulse 调度器** 管 L1 系统 tick；一个 **Agency 层** 管 L2 角色观察与提案；**L3 闸门** 决定谁可以真正 `dispatch` / 打扰 Founder。

---

## 2. 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│ L3 交互 / 审批（人 + 规则闸门）                                    │
│  · Founder HITL · CEO Turn 用户对话 · inbox 已读/采纳              │
│  · 用户正在输入 → 暂停 L2 Deliberate                             │
└───────────────────────────────┬─────────────────────────────────┘
                                │ 批准 / 合并提案
┌───────────────────────────────▼─────────────────────────────────┐
│ L2 Agency（角色自主 — Observe → Deliberate? → Propose）          │
│  · CEO：跨项目/跨角色观察 · 可选 LLM 合并提案 · 可 Act（派活）      │
│  · product/legal/dev/ops：本角色任务观察 · 默认只 Propose → inbox  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ signals / proposals
┌───────────────────────────────▼─────────────────────────────────┐
│ L1 Pulse（系统 tick — 确定性，默认 0 Token）                      │
│  execution · reconcile · presentation · commitments · delivery   │
│  · handoff · stream                                               │
└─────────────────────────────────────────────────────────────────┘
```

**命名约定（避免混淆）：**

| 词 | 含义 | 现有代码 |
|----|------|----------|
| **Pulse Engine** | 后台 asyncio 主循环 + 模块注册表 | 新建 `backend/app/pulse/` |
| **dashboard.pulse** | 派生统计（activeProjects 等） | `aggregates.recompute_pulse` — **保留，不改名** |
| **Agency Module** | 某角色的 Observe/Deliberate 插件 | 新建 `backend/app/agency/` |
| **Proposal** | 待 CEO/Founder 处理的结构化建议 | 扩 `inbox` + 新域 `proposals`（v1 可只用 inbox） |

---

## 3. L1 Pulse 模块注册表

所有 L1 模块实现同一接口：

```python
@dataclass
class PulseModule:
    id: str
    interval_sec: float          # 0 = 仅事件驱动
    cost_class: Literal["free", "io", "llm"]  # v1 全部 free/io
    enabled: bool
    run: Callable[[Session], PulseResult]
```

### 3.1 模块清单（v1 要做）

| id | 间隔 | cost | 职责 | 现有代码映射 | v1 行为 |
|----|------|------|------|--------------|---------|
| **execution** | 5s（有 pending）/ 60s（空闲） | io + 执行时 llm | 捞 `pending` 任务 → `run_role` → review → complete/fail | `engine._execute_runner` · `dispatcher` | **新建**；任务先入 `pending` |
| **reconcile** | 120s + 启动时 1 次 | free | 僵尸 `running`、orphan ack、feed 与 task 对齐 | `dispatch_feed.sync_dispatch_feed` | **新建** |
| **presentation** | 2s | free | `recompute_all` 中 presentation 部分；更新 stream sig | `presentation.derived` · `aggregates` | 从全量 recompute 拆出高频段 |
| **commitments** | 3600s | free | 逾期提醒、每日 digest | `scheduler_service.run_scheduler_tick` | **迁入** Pulse |
| **delivery** | 30s | free | HITL 待批扫描、artifact 状态推进提示 | `artifact_workflow` · `maybe_submit_artifact_review` | v1：规则扫描 → inbox |
| **handoff** | 10s | free | 消费 SQL `handoffs.status=pending` | `models.handoffs` · `engine` 写入 | v1：**新建 consumer** |
| **stream** | 1s | free | 计算各模块 signature，推 SSE delta | `api/orchestration.py` | **升级** 为多模块 payload |

### 3.2 模块清单（v1 不做 / v2）

| id | 说明 |
|----|------|
| **finance** | 成本汇总 tick — 仍随 mutation 触发即可 |
| **backup** | 运维层，不进应用 Pulse |
| **deliberation** | 会诊仍事件驱动，不纳入周期 tick |

### 3.3 execution 状态机（v1 必改）

```
dispatch / CEO 派活
       │
       ▼
   pending ──execution tick──► running ──run_role──► reviewing ──► done
       │                            │                      │
       │                            └──── fail ────────────┴──► failed
       │
       └── reconcile：running 超时无 agent_run → pending 或 failed
```

**改动点：** `dispatcher.dispatch_task(..., status="pending")`；execution 开始时改 `running` + `log_accept`。

---

## 4. L2 Agency 模块注册表

Agency 与 Pulse **共用调度器**，但走不同管道：

```python
@dataclass
class AgencyModule:
    role_id: str                   # ceo | product | legal | dev | ops
    observe_interval_sec: float
    observe: Callable[[dict], list[Signal]]      # 0 Token
    should_deliberate: Callable[[list[Signal]], bool]
    deliberate: Callable[[Session, list[Signal]], Proposal | None]  # 可选 LLM
    may_act: bool                  # 仅 ceo=True；其余 False
    act: Callable[[Session, Proposal], None] | None
```

### 4.1 观察范围（Observe 规则表）

#### CEO — `agency.ceo`（v1 全做 Observe；Deliberate v1 仅规则）

| signal_type | 触发条件 | 优先级 | 默认动作 |
|-------------|----------|--------|----------|
| `task.stuck` | `running` > 30min 且无 activity | high | proposal → inbox |
| `task.failed` | 任一 failed 未处理 | high | proposal + 可选 open commitment |
| `commitment.overdue` | 已有 scheduler 逻辑 | high | 已由 L1 commitments 写 inbox；CEO observe 合并展示 |
| `project.idle` | active 项目 48h 无 task/artifact 变更 | medium | proposal |
| `hitl.pending` | `hitlPending` 或 artifact `review` | high | proposal → 提醒 Founder |
| `brief.open_question` | `projectBriefs.openQuestions` 非空 | high | proposal → Founder 问询草稿 |
| `pipeline.gap` | `workflow_engine.get_next_steps` 产出 | medium | proposal |
| `handoff.pending` | SQL handoffs pending | medium | 交给 L1 handoff；CEO 仅观察 |

**Deliberate（v1）：** 不调用 LLM。将同类 signals **合并** 为 1 条 inbox（按 fingerprint 去重）。

**Deliberate（v2）：** 调用精简 CEO JSON turn，输出 `dispatch_plan` 草稿，仍须经 L3 或自动 Act 策略。

**Act（v1）：** 默认关闭。CEO 自主派活仍来自 **用户 CEO Turn** 或 **用户采纳 proposal**。

**Act（v1.1 开关）：** 设置页 **`ceoAutoDispatch.enabled`**。开启后，Phase B Agency 对 **低危 proposal** 可自动 `dispatch_task`，须同时满足：

| 闸门 | 默认（可在设置页改） |
|------|----------------------|
| `minDeliveryScore` | ≥ 80（近期 artifact 内审均分） |
| `maxRiskLevel` | `low` |
| `cooldownMin` | 同项目 15 分钟内不重复自动派活 |

**Act（v2）：** 可选 LLM Deliberate 后再 Act；或 `maxRiskLevel=medium` 扩大范围。

#### Product — `agency.product`（v1 Observe only）

| signal_type | 触发条件 | 默认动作 |
|-------------|----------|----------|
| `my.pending` | 本角色 pending 任务 | 无（等 execution） |
| `my.failed` | 本角色 failed | proposal → CEO inbox |
| `artifact.missing` | 项目 stage 需要 prd 且无 prd artifact | proposal → CEO |
| `brief.contradiction` | brief decisions 与 artifact 标题冲突（规则） | proposal → CEO |

#### Legal — `agency.legal`

| signal_type | 触发条件 | 默认动作 |
|-------------|----------|----------|
| `my.pending` / `my.failed` | 同上 | 同上 |
| `nda.stale` | lead/clarify 阶段超 7d 无法务 artifact | proposal → CEO |
| `hitl.legal_review` | legal artifact 待内审 | proposal → CEO |

#### Dev — `agency.dev`

| signal_type | 触发条件 | 默认动作 |
|-------------|----------|----------|
| `my.pending` / `my.failed` | 同上 | 同上 |
| `deliverable.blocked` | task `waitingOn` 非空 | proposal → CEO |
| `build.missing` | 阶段需要 demo/repo 且无 dev artifact | proposal → CEO |

#### Ops — `agency.ops`

| signal_type | 触发条件 | 默认动作 |
|-------------|----------|----------|
| `my.pending` / `my.failed` | 同上 | 同上 |
| `deploy.pending` | 阶段 5 / done 列无 ops 交付 | proposal → CEO |
| `sla.risk` | 项目 deadline 临近且无 done task | proposal → CEO |

### 4.2 频率与互斥

| 模块 | observe_interval | 备注 |
|------|------------------|------|
| agency.ceo | 300s（5min） | 有 `meta.orchestrationActive` 或用户 CEO 线程 pending 时 **跳过** |
| agency.product | 120s | 仅看 `roleId=product` |
| agency.legal | 180s | |
| agency.dev | 120s | |
| agency.ops | 180s | |

**优先级：** L1 `execution` 有 pending/running 时，所有 Agency **observe_interval × 2**（降频），Deliberate 暂停。

---

## 5. Proposal Bus（L2 → L3）

v1 不新建表，**复用 inbox**，增加字段：

```json
{
  "id": "inbox-abc123",
  "category": "proposal",
  "from": "product",
  "to": "ceo",
  "title": "建议：华为项目可推进 PRD 初稿",
  "preview": "pipeline.gap · proj-huawei",
  "projectId": "proj-huawei",
  "status": "active",
  "proposal": {
    "signalType": "pipeline.gap",
    "fingerprint": "pipeline.gap:proj-huawei:prd",
    "priority": "medium",
    "suggestedAction": "dispatch",
    "suggestedRole": "product",
    "suggestedTitle": "撰写 PRD 初稿",
    "expiresAt": "2026-05-28T12:00:00+08:00"
  }
}
```

### 5.1 去重（fingerprint + TTL）

| 规则 | 值 |
|------|-----|
| 同 fingerprint 且 inbox `status=active` | 不重复创建 |
| active proposal TTL | 72h 后 auto `expired` |
| 同项目同 signal_type 每日最多 | CEO 3 条；其他角色各 2 条 |

### 5.2 Founder 打扰策略（L3）

| 类型 | 是否可触达 Founder | 条件 |
|------|-------------------|------|
| `brief.open_question` | 是 | 同一问题 24h 内最多 1 次 |
| `hitl.pending` | 是 | 已有 artifact，立即 |
| 角色 → CEO 的 `proposal` | 否 | 仅 CEO inbox |
| CEO → Founder 问询 | 是 | 须 `priority=high` 或用户开启「主动提醒」 |

---

## 6. 事件总线（即时 vs 周期）

除周期 tick 外，以下事件 **立即 enqueue 对应模块**（不必等 interval）：

| 事件 | 来源 | 触发模块 |
|------|------|----------|
| `ceo.brief` | POST /ceo/brief | execution（若 schedule）· agency.ceo observe |
| `task.completed` | execution | presentation · agency.ceo · delivery |
| `task.failed` | execution | agency.{role} · agency.ceo · commitments |
| `hitl.approved` / `hitl.rejected` | API | delivery · agency.ceo |
| `inbox.resolved` | 用户采纳 proposal | execution（若 proposal 含 dispatch） |
| `artifact.created` | execution | delivery · agency.ceo |
| `startup` | Pulse 进程启动 | reconcile · presentation |

---

## 7. Token 预算

| 路径 | v1 | v2 |
|------|----|----|
| L1 全部 Pulse tick | **0** | 0 |
| Agency Observe | **0** | 0 |
| Agency Deliberate（CEO LLM） | **0（v1 不做）** | ≤ 6 次/小时 |
| Agency Deliberate（角色 LLM） | **0（v1 不做）** | ≤ 2 次/角色/小时 |
| execution `run_role` | 按任务 | 按任务 |
| 用户 CEO Turn | 按对话 | 按对话 |

**硬规则：** Pulse/Agency 调度代码 **不得** import `chat_completion`；LLM 只出现在 `run_role`、用户发起的 `run_ceo_turn`、以及 v2 的 `agency.deliberate` 包内。

---

## 8. SSE / API 契约（v1）

### 8.1 升级 `GET /orchestration/stream` → `GET /pulse/stream`

兼容 v1：旧端点保留 1 个版本，内部转发。

```json
{
  "v": 1,
  "at": "2026-05-21T10:00:00+08:00",
  "modules": {
    "presentation": { "sig": "a1b2", "changed": true },
    "execution": { "pending": 1, "running": 2, "active": true },
    "agency": { "openProposals": 3, "lastCeoObserve": "..." },
    "inbox": { "unread": 5 },
    "orchestration": { "feedCount": 12, "active": true }
  }
}
```

前端策略：

| changed 模块 | 前端动作 |
|--------------|----------|
| `presentation` | `GET /dashboard` 或仅 `GET /presentation/overview`（v2 拆端点） |
| `inbox` | 刷新收件箱 badge |
| CEO thread pending | 已有 `pollCeoThreadUntilSettled` |

### 8.2 运行时状态 `meta.pulseRuntime`

```json
{
  "meta": {
    "pulseRuntime": {
      "startedAt": "...",
      "lastTickAt": "...",
      "modules": {
        "execution": { "lastRun": "...", "lastResult": "ran 1 task", "nextInSec": 5 },
        "agency.ceo": { "lastObserve": "...", "signals": 2, "proposalsCreated": 0 }
      },
      "paused": false,
      "pauseReason": null
    }
  }
}
```

供设置页 / 调试展示，**证明系统在跑**。

---

## 9. 代码落位（v1 文件规划）

```
backend/app/
├── pulse/
│   ├── __init__.py
│   ├── coordinator.py      # asyncio 主循环、注册表、事件队列
│   ├── modules/
│   │   ├── execution.py
│   │   ├── reconcile.py
│   │   ├── presentation.py
│   │   ├── commitments.py
│   │   ├── delivery.py
│   │   ├── handoff.py
│   │   └── stream.py
│   └── signatures.py       # 各模块 sig 计算
├── agency/
│   ├── __init__.py
│   ├── signals.py            # Signal / Proposal 类型
│   ├── bus.py                # fingerprint 去重、写 inbox
│   ├── modules/
│   │   ├── ceo.py
│   │   ├── product.py
│   │   ├── legal.py
│   │   ├── dev.py
│   │   └── ops.py
│   └── rules/                # 各 signal 纯函数规则
│       ├── tasks.py
│       ├── pipeline.py       # 包装 workflow_engine.get_next_steps
│       └── artifacts.py
├── api/
│   └── pulse.py              # /pulse/stream · /pulse/status
└── main.py                   # startup: asyncio.create_task(pulse_loop)
```

**不动原则：** `ceo_turn` 用户对话路径保持；workflow 改为 **入队 pending tasks**，不在 HTTP 内联跑完。

---

## 10. v1 实施范围（确认后开工）

### Phase A — 能跑（P0，先做）

- [ ] `pulse.coordinator` + 进程内 asyncio 循环
- [ ] `execution` 模块：pending → running → 现有 runner 链路
- [ ] `reconcile` 模块：启动 + 120s
- [ ] `dispatch_task` 默认 `pending`
- [ ] `handoff` consumer
- [ ] `meta.pulseRuntime` 写入
- [ ] `/pulse/stream` 多模块 sig
- [ ] 测试：pending 任务在无 HTTP 情况下被执行完

### Phase B — 能看（P1）

- [x] `commitments` 迁入 Pulse
- [x] `presentation` 高频 tick + 前端按需 refresh
- [x] `delivery` 规则扫描
- [x] Agency **Observe only**：ceo + 四角色
- [x] Proposal inbox + fingerprint 去重

### Phase C — 能想（P2，v2）

- [ ] CEO Deliberate（LLM 合并提案）
- [ ] 用户采纳 proposal → 自动 dispatch
- [ ] 角色 Deliberate（可选）
- [ ] CEO 低危 auto-dispatch 配置

---

## 11. 已知未覆盖（刻意留 v2+）

| 话题 | 说明 |
|------|------|
| 多实例 / 分布式锁 | v1 单进程 SQLite，假定单 worker |
| Founder Profile 驱动 observe 阈值 | v2 读 profile 调整频率 |
| 项目级 pause / quiet hours | v2 `meta.agencyPausedProjects` |
| 向量检索 / 长记忆 | 不在本规格范围 |
| Agent 群聊 | 违反星型调度，不做 |
| 外部 webhook / 邮件 ingress | 仍走现有 intake，不进 Pulse |
| 完整 SLA 数值调优 | 表内阈值为初始值，上线后按真实数据调 |

---

## 12. 验收口径（v1 完成定义）

1. CEO Turn 派活后 **关闭浏览器**，任务仍能在 30s 内开始执行并产出 artifact 或 failed。
2. 服务重启后 **无永久 running 僵尸**；pending 队列继续消费。
3. `handoffs` pending 在 60s 内被消费或显式失败。
4. SSE 推送后前端 **不全量 2s 轮询**（仅 sig 变化时拉 dashboard）。
5. Agency Observe 产生 proposal 时 **不消耗 LLM**；同 fingerprint 不刷屏。
6. 用户 CEO 对话进行中 **无自主 inbox 打扰**（pauseReason=`ceo_thread_active`）。

---

## 13. 与路线图关系

本规格 **不替代** [CEO-ORCHESTRATION-ROADMAP.md](./CEO-ORCHESTRATION-ROADMAP.md) 的产品目标（G1–G8），而是补齐其 **Runtime 层**：

```
CEO-ORCHESTRATION-ROADMAP  = 做什么（产品能力）
PULSE-AGENCY-SPEC          = 什么时候做、谁来做、花不花 Token
```

确认本 draft 后，Implementation 顺序：**Phase A → B**；Phase C 单独开 v2 draft。

---

## 14. 运行时配置（`meta.runtimeSettings` + 设置页）

**原则：** 阈值与开关 **不进代码常量**；默认值在 `runtime_settings.DEFAULT_RUNTIME_SETTINGS`，持久化在 `dashboard.meta.runtimeSettings`，UI 在 **设置 → 编排运行时**。

### 14.1 存储位置

```json
{
  "meta": {
    "runtimeSettings": {
      "pulse": { "enabled": true, "executionIntervalSec": 5, "runningStaleMin": 30, ... },
      "agency": { "enabled": false, "ceoObserveIntervalSec": 300, ... },
      "ceoAutoDispatch": {
        "enabled": false,
        "minDeliveryScore": 80,
        "maxRiskLevel": "low",
        "cooldownMin": 15
      },
      "founderNotify": { "openQuestionCooldownHours": 24, ... }
    }
  }
}
```

### 14.2 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/runtime/settings` | 读合并后的 effective settings |
| PATCH | `/api/v1/runtime/settings` | 部分更新（deep merge） |
| POST | `/api/v1/runtime/ceo-auto-dispatch` | 快捷切换自动派活 `{ "enabled": true }` |

### 14.3 设置页字段（v1）

| UI 标签 | 键 | 默认 |
|---------|-----|------|
| 启用 Pulse 后台心跳 | `pulse.enabled` | true |
| 任务执行间隔（秒） | `pulse.executionIntervalSec` | 5 |
| Running 超时重置（分钟） | `pulse.runningStaleMin` | 30 |
| CEO 全局观察间隔（秒） | `agency.ceoObserveIntervalSec` | 300 |
| **CEO 自动派活** | `ceoAutoDispatch.enabled` | **false** |
| 自动派活 · 最低交付分 | `ceoAutoDispatch.minDeliveryScore` | 80 |
| 自动派活 · 最高风险级别 | `ceoAutoDispatch.maxRiskLevel` | low |
| 自动派活 · 同项目冷却（分钟） | `ceoAutoDispatch.cooldownMin` | 15 |
| Founder 问询冷却（小时） | `founderNotify.openQuestionCooldownHours` | 24 |

环境变量 **`OPC_PULSE_ENABLED=0`** 可全局关闭 Pulse 循环（测试 / 调试），优先级高于 `pulse.enabled`。

### 14.4 CEO 自动派活开关逻辑（Phase B 消费）

```
proposal 进入 inbox
       │
       ▼
ceoAutoDispatch.enabled == false ──► 仅 inbox，等人采纳
       │
       enabled == true
       ▼
proposal.risk <= maxRiskLevel
AND recent_delivery_score >= minDeliveryScore
AND project_cooldown elapsed
       ▼
dispatch_task(pending) → Pulse execution
```

交付分来源：近期 `review_artifact` pass 率 / 规则分（Phase B 实现）；v1 只存配置，不自动 Act。

