# OPC Studio · Agent 编排与协作设计

| 项 | 内容 |
|----|------|
| 版本 | v1.0 草案 |
| 状态 | 与 Founder 确认 · **避免「纯前端 + Chat」** |
| 关联 | [PRD.md](./PRD.md) · [BACKEND.md](./BACKEND.md) · [IMPLEMENTATION.md](./IMPLEMENTATION.md) · [API.md](./API.md) |

---

## 1. 你的担心是对的

若 Phase 2 只做完 **SQLite + REST + 状态机**，系统本质上是：

```
你 → Web 看板点按钮 → 数据库改字段
CEO FAB → 存一条 chat → 无真实推理与调度
```

这 **不是** OPC Agent 集群，而是 **CRM + 审批流 UI**。

**本项目必须是：**

```
你 → CEO Agent（理解、立项、调度）
CEO → 派 Task 给 产品/法务/开发/运营 Agent
各 Agent → 产出 artifact → Handoff 给下一角色或 CEO
CEO → 打包 HITL 呈报给你 → 你批 → 工作流继续
```

因此后端除 **数据层（Phase 2）** 外，必须有 **编排层（Phase 3）**；且 Phase 2 建表/API 时要 **为编排预留**，不能事后硬补。

---

## 2. 设计原则（不是 Agent 自由群聊）

| ❌ 不做 | ✅ 要做 |
|--------|--------|
| 五个 Agent 在群里 **自由** @ 互聊、无上限多轮 | **CEO 星型调度**：只有 CEO 派活、汇总、升级 |
| 把聊天记录当项目进度 | **Task + Artifact + Handoff** 驱动状态 |
| 前端按钮直接改 project.progress | **Orchestrator** 根据事件改状态 |
| 每个 Tab 一个独立 Chatbot | 看板是 **编排控制面**，Chat 是 **Ingress 之一** |
| — | **例外**：CEO 在特定条件下开 **会诊室**（见 §4.1），有议程、有上限、必收口 |

**一句话：** 常态协作靠 **工作流事件**；**会诊室** 是 CEO 主持的 **有限澄清**，不是第五种编排模式。

---

## 3. 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│  Ingress 接入层                                               │
│  Web CEO FAB · 飞书 @CEO · （未来）微信                        │
└───────────────────────────┬─────────────────────────────────┘
                            │ InboundMessage
┌───────────────────────────▼─────────────────────────────────┐
│  Orchestrator 编排层（Phase 3 核心）                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Project     │  │ Task         │  │ HITL Gate           │ │
│  │ Workflow    │  │ Dispatcher   │  │ (4 卡点)            │ │
│  │ (5阶段+PoC) │  │ (CEO)        │  │                     │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
│         │                  │                    │             │
│         └──────────────────┴────────────────────┘             │
│                            │ Dispatch / Handoff / Escalate    │
└───────────────────────────┼─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Role Runners 执行层（5 个 Agent 实例）                        │
│  产品 · 法务 · 开发 · 运营 · （CEO 自身也跑 LLM 推理）          │
│  输入：Task + 上下文 artifacts                                 │
│  输出：artifact 文件 + task 进度 + handoff 事件                │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Control Plane 控制面（Phase 2 已实现 API + DB）               │
│  projects · tasks · artifacts · inbox · hitl · finance        │
└─────────────────────────────────────────────────────────────┘
```

**Phase 2 = 控制面**  
**Phase 3 = 编排层 + 执行层**  
两者缺一不可。

---

## 4. 六种协作原语（Agent 间交互 vocabulary）

所有 Agent 间交互 **只** 通过这六种事件，便于审计、重放、测试：

| 原语 | 方向 | 含义 | 写入 |
|------|------|------|------|
| **Dispatch** | CEO → 角色 | 「请执行 Task X」 | `tasks.status=running`，`agent_runs` 启动 |
| **Handoff** | 角色 → CEO/下一角色 | 「产出物 Y 已完成，请接手」 | `handoffs` 表 + `artifacts` 文件 |
| **Wait** | 角色 → 编排器 | 等 Founder HITL / 等另一 Task | `tasks.status=waiting`，`waitingOn` |
| **Escalate** | 任意 → CEO | 风险/阻塞/超预算 | `alerts` + inbox 必读 |
| **HITL Request** | CEO → Founder | 打包呈报审批 | `hitl_queue` + inbox |
| **Complete** | 编排器 | 项目阶段推进 | `projects.stage` / `pipelineColumn` |

**没有** `AgentA.chat(AgentB, "你好")` 这种自由消息。

**例外原语（第 7 种，仅 CEO 可发起）：**

| 原语 | 方向 | 含义 | 写入 |
|------|------|------|------|
| **Deliberate** | CEO → 多角色（会诊） | 需求模糊时 **有限轮次** 澄清，Founder **旁观** | `deliberation_sessions` + `deliberation_turns` |

---

## 4.1 例外通道：CEO 会诊室（Clarification Room）

> **Founder 已确认需要：** 需求很模糊、自己拿不准时，由 **CEO 发起** 多角色共同讨论；你在群里 **看讨论**，但 **非常态**——只有 CEO 判断需要时才开。

### 4.1.1 和「自由群聊」的本质区别

| 维度 | ❌ 自由群聊（不做） | ✅ CEO 会诊室（做） |
|------|---------------------|---------------------|
| 谁发起 | 任意 Agent 随时开聊 | **仅 CEO**（或你 @CEO 要求，仍由 CEO 决定是否开） |
| 目的 | 无固定出口 | **澄清一个决策点**，产出 **Decision Memo** |
| 轮次 | 无限 | **硬上限**（建议 1–2 轮，每角色每轮 1 条结构化发言） |
| 参与人 | 全员常驻 | CEO **点选** 2–3 个相关角色 |
| 编排 | 与 Task 链并行乱飞 | 会诊期间 **暂停** 该项目其他 Dispatch |
| Founder | 被迫下场调解 | **默认旁观**；可随时插话，但不替代 CEO 收口 |
| 结束 | 聊完就散 | CEO **总结 → 关室 → Dispatch 正式 Task** 或 **HITL 请示你** |

**结论：** 这是星型调度上的 **子状态机**，不是把 OPC 改成 AutoGen GroupChat。

### 4.1.2 何时 CEO 应发起（白名单）

仅当 **至少一条** 成立，且 CEO 评估「单点 Dispatch 不够」：

| 触发条件 | 示例 |
|----------|------|
| **Brief 模糊** | 客户只说「做个审批流」，预算/范围/交付形态不清 |
| **跨域冲突** | 产品 scope 与法务合同条款、开发工期 **无法由 CEO 单方面拍板** |
| **评估立项 · 澄清分支** | 阶段 2 转移表 `assess → clarify`（与 architecture「不接/澄清/立项」一致） |
| **你明确要求** | 「让产品和法务先对齐一下再报给我」→ CEO 开室，不是五个 Agent 自己拉群 |

**不应发起：** 已有清晰 Task、单角色能完成、纯执行进度同步（用 Handoff + activity 即可）。

### 4.1.3 会诊流程（编排视角）

```
[触发] Brief 模糊 / assess→clarify / Escalate(scope_conflict)
         │
         ▼
CEO Runner 判断 → Deliberate(open)
         │
         ├─ project.workflow_state = deliberating   （暂停其他 Dispatch）
         ├─ 选定 roles: [product, legal] + agenda 3 问
         └─ 推送 SSE: deliberation.opened → 看板「会诊」Tab / 项目内抽屉
         │
         ▼
Round 1（结构化，非自由聊天）
  CEO 主持：逐角色调用 Runner，每人回答 agenda 同一套问题
  写入 deliberation_turns（role, round, content, tokens）
  Founder 只读订阅；可选 POST 插话 → 记入 turns（author=founder）
         │
         ▼
[可选 Round 2] 仅当 CEO 发现仍有关键分歧（最多 +1 轮）
         │
         ▼
CEO 合成 Decision Memo → artifact art-decision-*
         │
         ├─ 若仍要你拍板 → HITL Request（inbox）
         └─ 若 CEO 可执行 → Deliberate(close) + Dispatch 下游 Tasks
         │
         ▼
project.workflow_state = active
orchestration_events: DeliberationOpened | TurnRecorded | DeliberationClosed
```

### 4.1.4 风险与缓解（不会「搞垮编排」的前提）

| 风险 | 严重吗 | 缓解 |
|------|--------|------|
| Token 成本飙升 | 中 | 上限：≤3 角色 × ≤2 轮；整室计入 `agent_runs` 预算；超预算 CEO 必须 Escalate 而非继续聊 |
| 讨论发散、无结论 | 中 | **议程必填**（CEO 开场列出待决问题）；最后一轮 **只允许 CEO 发言**（合成） |
| 与 Task 链状态打架 | 高（若不设计） | `deliberating` 全局锁：该项目 **禁止** 并行 Dispatch；关室后才恢复 |
| 审计/看板噪音 | 低 | turns 进专用表，**不**混进 `ceo_messages`；项目活动流只展示摘要 + Memo 链接 |
| Agent 互相 @ 跑飞 | 高（自由群聊） | **禁止 Agent→Agent 直连**；Orchestrator **代 CEO 顺序调用** Runners，非 Multi-Agent 互聊 API |
| Founder 被拖下水 | 低 | 默认旁观；HITL 只在 Memo 仍不确定时触发 |

**实现难度：** **中等**，建议放在 **Phase 3e**（编排骨架 + 单角色 Runner 跑通之后）。  
**不是 Phase 2  blocker**：Phase 2 只需 **预留表 + 看板只读 UI 占位**；Phase 3a–3c 完全不依赖会诊也能验收 Acme 主链。

### 4.1.5 数据模型（Phase 2 预留）

```sql
deliberation_sessions (
  id, project_id,
  opened_by,                    -- ceo
  agenda_json,                  -- ["范围边界?", "PoC 还是全量?", ...]
  participant_roles_json,       -- ["product","legal"]
  status,                       -- open | closed | cancelled
  max_rounds, current_round,
  decision_artifact_id,         -- 关室时挂载
  opened_at, closed_at
)

deliberation_turns (
  id, session_id,
  round, author,                -- ceo | product | ... | founder
  content, agent_run_id,
  created_at
)
```

**API（Phase 3e，摘要）：** `GET /projects/{id}/deliberation` · `POST .../deliberation/{sid}/founder-note`（旁观插话）

---

## 5. 项目工作流（5 阶段 + PoC 分支）

与 [architecture.html](../architecture.html) 业务全景一致，编排器按 **项目 stage** 驱动：

```
阶段1 线索/获客
  └─► 运营：登记 Pipeline（Dispatch ops）

阶段2 评估立项
  └─► CEO：7项评估 + 风险（Dispatch ceo）
  └─► 分支：不接 / 澄清 / 立项 / 走 PoC

阶段3 方案签约
  ├─► 产品：PRD（Dispatch product）
  ├─► HITL-1：你批 PRD
  ├─► 法务：报价/SOW（Dispatch legal，依赖 PRD handoff）
  ├─► HITL-2：你批报价
  └─► [可选 PoC 分支] 开发：Demo（Dispatch dev）→ 回流阶段2/3

阶段4 开发交付
  ├─► 开发：交付物 + 自测（Dispatch dev）
  ├─► 运营：验收清单 + 客户邮件草稿（Dispatch ops）
  ├─► HITL-3：你批交付物
  └─► HITL-4：你批对外文案

阶段5 收尾续费
  ├─► 运营：结项 ZIP（Handoff）
  ├─► 法务：收款跟踪（Dispatch legal）
  └─► CEO：续费/新需求 → 回到阶段1
```

**编排器实现：** 每个 `(project.stage, event)` 对应一张 **转移表**（可存 YAML 或 DB），而非硬编码 if-else 散落各处。

---

## 6. 一次完整协作示例（Acme · Mock 故事线）

```
1. [Ingress] 你向 CEO 投递 Beta 需求纪要
   → ceo_router 创建 InboundMessage
   → Orchestrator: 项目 proj-beta 阶段2，Dispatch task-ceo-1

2. [CEO Runner] 完成风险评估 artifact art-memo-beta
   → Handoff(ceo → founder, type=request) → inbox 请示 PoC
   → 你点「同意 PoC」→ Resolve event

3. [Orchestrator] 转移：Dispatch task-dev-2 (PoC)，Wait task-product-2

4. [Dev Runner] Acme staging 交付 art-demo-acme
   → Handoff(dev → ceo, artifact=art-demo-acme)
   → Orchestrator: 创建 HITL-3，Dispatch task-ceo-2 打包

5. [CEO Runner] 汇总呈报
   → HITL Request hitl-3-acme → inbox

6. [你] 批准 HITL-3
   → Orchestrator: 阶段5，Dispatch ops 结项清单
   → closure in_closure → 导出客户 ZIP
```

**看板上的每个 Tab 都是这条链的投影**，不是独立功能。

---

## 7. 编排层数据模型（Phase 2 预留 · Phase 3 使用）

Phase 2 建表时 **一并创建**（可先空表），避免 Phase 3 大改：

```sql
-- Agent 一次执行（绑定 Task）
agent_runs (
  id, task_id, role_id, project_id,
  status,          -- queued | running | succeeded | failed | cancelled
  model, tokens_in, tokens_out, cost_cny,
  started_at, finished_at, error_message
)

-- 角色间交付事件（核心协作边）
handoffs (
  id, project_id,
  from_role, to_role,           -- ceo | product | ...
  artifact_id, task_id,
  kind,                         -- deliverable | review | escalation
  status,                       -- pending | accepted | rejected
  note, created_at
)

-- 编排事件日志（可重放、调试）
orchestration_events (
  id, project_id,
  type,                         -- Dispatch | Handoff | HITLApproved | ...
  payload_json,
  caused_by,                    -- founder | ceo | system | role_id
  at
)

-- 工作流定义（按项目类型）
workflow_templates (
  id, name,                     -- e.g. agent_delivery_default
  stages_json,                  -- 转移表
  hitl_gates_json
)

-- CEO 会诊室（§4.1 · Phase 2 建空表，3f 使用）
deliberation_sessions (
  id, project_id, opened_by, agenda_json, participant_roles_json,
  status, max_rounds, current_round, decision_artifact_id,
  opened_at, closed_at
)

deliberation_turns (
  id, session_id, round, author, content, agent_run_id, created_at
)
```

**与现有表关系：**

| 已有 | 编排层用法 |
|------|------------|
| `tasks` | Dispatch 创建/更新 |
| `artifacts` | Handoff 挂载产出物 |
| `inbox` / `hitl_queue` | HITL Request 呈报 Founder |
| `ceo_messages` | Ingress 原始消息，触发 Orchestrator |
| `token_runs` | 可合并进 `agent_runs` 或作明细 |

---

## 8. Role Runner 设计（每个 Agent 怎么跑）

```python
class RoleRunner:
    role_id: RoleId
    config: RoleConfig          # model, api_base_url, api_key

    async def run(self, task: Task, context: RunContext) -> RunResult:
        """
        context 包含：
        - project 摘要
        - 依赖 artifacts（如前序 PRD）
        - charter + 工具列表
        """
        # 1. 组装 system prompt（角色 charter + 阶段约束）
        # 2. 调 LLM（httpx → api_base_url）
        # 3. 解析结构化输出 → artifact.md + progress_note
        # 4. 写文件 + 更新 task + emit Handoff
        # 5. 记 agent_runs + token 成本
```

**CEO Runner 额外能力：**

- 解析 Founder 自然语言 → 结构化 `Brief`（客户/需求/预算）
- **Dispatcher**：决定 Dispatch 哪个角色、是否 HITL
- **Summarizer**：周报、HITL 打包文案

**工具（Tools）：** 按角色限制，如 ops 可写 Pipeline，dev 可跑代码/OCR，legal 只读合同模板——通过 `role_config.tools` 白名单。

---

## 9. Orchestrator 设计（CEO 的「脚本引擎」）

```python
class Orchestrator:
    async def on_event(self, event: OrcheEvent) -> None:
        match event.type:
            case "InboundBrief":
                await self.ceo_assess_and_dispatch(event)
            case "Handoff":
                await self.route_handoff(event)
            case "HITLApproved":
                await self.advance_workflow(event)
            case "HITLRejected":
                await self.rework_or_escalate(event)
            case "TaskCompleted":
                await self.check_dependencies_and_dispatch(event)
            case "DeliberationOpened":
                await self.pause_project_dispatch(event.project_id)
            case "DeliberationClosed":
                await self.resume_and_dispatch_from_memo(event)
```

**工作流引擎选型（Phase 3 决策）：**

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A. 自研转移表 + Python** | 轻、完全贴合 5 阶段 | 要自己写并行/重试 |
| **B. LangGraph** | 图编排、HITL 节点成熟 | 学习成本、略重 |
| **C. YAML + 小型 DSL** | 可配置、你改流程不用改代码 | 要先设计 DSL |

**建议：** Phase 3a 用 **A（转移表）** 跑通 Acme 一条链；复杂后再评估 B。

---

## 10. 与 Phase 2 / 前端的关系

| 层 | 谁消费 | 说明 |
|----|--------|------|
| Phase 2 API | 前端看板 | 展示 tasks / inbox / artifacts **结果** |
| Phase 3 Orchestrator | 后台异步 | 生产这些结果 |
| SSE `/events` | 前端 | 推送 `task.updated` / `handoff.created` |

**Phase 2c 写操作（你点批准 HITL）** 在 Phase 3 应改为：

```
你点批准 → API → Orchestrator.on(HITLApproved) → 自动 Dispatch 下游 Task
```

Phase 2c 可先 **硬编码副作用**（与 Mock 一致）；Phase 3 **同一 API 入口**，内部改调 Orchestrator。

**CEO FAB 在 Phase 3：**

```
POST /ceo/brief → InboundMessage → Orchestrator（非固定 ack 字符串）
```

---

## 11. Phase 3 实施分期（编排 + Agent）

| 阶段 | 交付 | 验收 |
|------|------|------|
| **3a · 编排骨架** | `Orchestrator` + `orchestration_events` + 转移表（Acme 单项目） | 手动触发 event，task 链自动推进 |
| **3b · CEO Runner** | 纪要解析 + Dispatch + HITL 打包 | 飞书/Web 投递 → 自动创建 task |
| **3c · 角色 Runners** | product / dev / ops / legal 四个 Runner | Handoff 链：PRD → SOW → Demo |
| **3d · 工具与成本** | 按角色 tools + `agent_runs` 记账 | 经营页成本随 LLM 调用更新 |
| **3e · 并行与 PoC 分支** | Beta PoC 分支、多项目并行 | 两项目同时跑不互相踩 |
| **3f · CEO 会诊室** | `Deliberate` 原语 + 旁观 UI + Decision Memo | 模糊 Brief → 开室 → 关室 → Dispatch/HITL |

**依赖：** Phase 2a–c 完成（控制面 + 写 API）。**3f 依赖 3a–3c**，可与 3e 并行。

**会诊室 UI（Mock 可先做静态）：** 项目工作室内「会诊」抽屉，只读 turn 列表 + Memo；CEO FAB 不直接开室，开室是 Orchestrator 事件结果。

---

## 12. 修订后的总路线图

```
Phase 1   ✅ Mock 看板（验证 UX）
Phase 2   控制面 API + DB + 文件
          └─ 预留 handoffs / agent_runs / orchestration_events 表
Phase 3   编排层 + Role Runners（本项目「是 Agent 公司」的分水岭）
Phase 4   飞书 Ingress 深度集成 · 可选上云
```

**时间感（兼职）：**

- Phase 2：3–4 周  
- Phase 3a–3c：**4–6 周**（真正 LLM + 编排，不能省）

---

## 13. IMPLEMENTATION 计划需同步的变更

已在 [IMPLEMENTATION.md](./IMPLEMENTATION.md) 中补充：

1. Phase 2a 建表 **包含** §7 编排预留表  
2. Phase 2c 写 API 设计为 **Orchestrator 可 hook** 的入口  
3. 新增 **Phase 3 章节**（3a–3e），与本文档对齐  
4. 验收标准增加：**至少一条 Acme 全链路由 Orchestrator 自动跑通**（Phase 3c Done）

---

## 14. Founder 确认项（编排专项）

| # | 问题 | 建议 |
|---|------|------|
| 1 | Agent 协作模型 | CEO 星型 + Handoff；**例外** CEO 会诊室（§4.1），非常态 |
| 2 | Phase 2 是否预留编排表 | **是**，含 `deliberation_*` 空表 |
| 3 | Phase 3 工作流引擎 | 先自研转移表，LangGraph 备选 |
| 4 | CEO FAB 固定 ack → 真实推理 | Phase 3b 改 |
| 5 | 是否接受「Phase 2 完成后仍无 LLM，但架构就绪」 | 是（控制面必须先稳） |

---

## 15. 文档索引

| 文档 | 职责 |
|------|------|
| PRD | 产品做什么 |
| BACKEND | 技术栈与部署 |
| API | 前后端契约 |
| IMPLEMENTATION | Phase 2 怎么落地 |
| **AGENTS.md（本文）** | **Agent 怎么协作、编排怎么设计** |
