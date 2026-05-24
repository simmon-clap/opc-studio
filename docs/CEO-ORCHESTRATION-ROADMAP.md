# CEO Agent 编排迭代规划

| 项 | 内容 |
|----|------|
| 版本 | v0.2 |
| 状态 | **Phase 0–5 代码落地** · Phase 2 Review **⚠️ 规则分，非 LLM** · [DEV-STATUS.md](./DEV-STATUS.md) |
| 关联 | [AGENTS.md](./AGENTS.md) · [API.md](./API.md) · [BACKEND.md](./BACKEND.md) · [IMPLEMENTATION.md](./IMPLEMENTATION.md) |
| 代码基线 | OPC Studio **v0.9.x** |

---

## 1. 北极星：你要的 CEO 是什么

Founder 与 CEO 的协作目标（验收口径）：

| # | 能力 | 验收场景（举例） |
|---|------|------------------|
| G1 | **无脑交流** | 随便聊、补充、催促，不必记「让法务写 NDA」句式 |
| G2 | **理解需求** | 丢会议纪要/附件，CEO 提取客户、决策、待办、截止时间 |
| G3 | **可靠派活** | CEO 口头承诺 = 后台必派 Task，项目归属正确 |
| G4 | **监督进度** | 承诺未兑现、Task 失败、超时 → inbox 提醒，CEO 主动 cue |
| G5 | **内审质检** | CEO 审员工产出，不合格打回修订 + 改进意见，循环至合格 |
| G6 | **交付给你** | CEO 满意后才进 Founder HITL / 工作室定稿 |
| G7 | **懂你的风格** | 回复长度、文档严谨度、哪些事必须请示 — 越来越贴你 |
| G8 | **推进流程** | 按项目 stage 提示「还缺什么、下一步谁干」，而非聊天复读 |

**设计约束（继承 AGENTS.md，不推翻）：**

- CEO **星型调度**，Agent 之间不自由群聊
- 进度以 **Task + Artifact + Handoff** 为准，不以聊天记录为准
- **轻量本地**：SQLite + 文件，不做多租户 / 重型 MQ / 默认向量库
- **Mock JSON 兼容**：新字段可增，旧前端字段不删（camelCase）

---

## 2. 现状基线（v0.3.0）

### 2.1 已有能力

```
Ingress          POST /ceo/brief（文本）
Orchestrator     engine.py · dispatch_planner · directives · transitions
Runners          5 角色 LLM + deliverable 模板/校验
控制面           dashboard JSON · tasks · artifacts · inbox · hitlQueue
工作室           kind/viewer/版本/diff · HITL-Artifact
会诊             deliberation（有限轮次）
```

### 2.2 已知架构问题（规划必须正视）

| 问题 | 影响 | 优先级 |
|------|------|--------|
| **聊天 LLM 与调度 LLM 分离** | CEO 说派活但不执行（NDA 事件） | P0 |
| **项目 ID 启发式** | 追问类消息关联错项目 | P0 |
| **`dashboard` 整包 JSON** | 并发写、难索引 commitments | P1 |
| **`dispatch_planner` ↔ `transitions` 循环 import** | 部分路径 import 失败 | P1 |
| **Background workflow 无可见 telemetry** | 失败静默 | P1 |
| **质检仅规则分 + Founder HITL** | 无 CEO→员工修订环 | P2 |
| **`reject_artifact` 不触发重派** | 驳回后人工再聊 | P2 |
| **无文件 ingress** | 无法丢纪要 | P3 |
| **无 Founder Profile** | 无风格记忆 | P4 |
| **stage 转移表未统一** | kickoff/HITL 逻辑散落 | P4 |

### 2.3 接口现状（与规划的关系）

| 端点 | 现状 | 规划期是否改动 |
|------|------|----------------|
| `POST /ceo/brief` | `{ text }` → chat + background workflow | **扩展** multipart / attachments |
| `GET /dashboard` | 全量聚合 | 增 `commitments` · `projectBriefs` 域 |
| `POST /hitl/{id}/reject` | Founder 驳回 | 保持；新增 CEO 内审事件 |
| `artifacts` CRUD | 已有版本/approve | 增 `revision` 状态与 `reviewNotes` |
| 无 | — | 新增 `GET/PATCH /founder/profile` · `GET /commitments` |

**原则：** Phase 1–2 以 **dashboard JSON 增域 + orchestrator 内逻辑** 为主，避免大规模拆表；Phase 3 再把 commitments 迁 SQL 表（可选）。

---

## 3. 目标架构：CEO Operating Loop

```
                    ┌──────────────────────────────────────┐
  Founder           │         CEO Turn（单次结构化回合）      │
  文本 / 文件  ───► │  Input: thread + brief + profile     │
                    │         + attachments                 │
                    └─────────────────┬────────────────────┘
                                      │
                    ┌─────────────────▼────────────────────┐
                    │  Output (JSON, 机器可读)               │
                    │  · reply          → ceoThread         │
                    │  · projectId      → activeProject     │
                    │  · briefDelta     → projectBriefs     │
                    │  · commitments    → 待办/提醒          │
                    │  · dispatch       → Task 派活         │
                    └─────────────────┬────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
    Role Runners              Supervisor Loop              Review Loop
    (product/legal/…)         (SLA / 失败 / 超时)         (CEO 审 artifact)
          │                           │                           │
          └───────────────────────────┴───────────────────────────┘
                                      ▼
                         Handoff → inbox / HITL → Founder
                                      ▲
                         Scheduler（主动 cue / 周报 / 提醒）
```

**记忆分层（防臃肿）：**

| 层 | 内容 | 大小 | 用途 |
|----|------|------|------|
| L0 | `ceoThread` 原文 | 增长 → 按项目摘要归档 | 审计、补上下文 |
| L1 | `projectBriefs` | ~1KB/项目 | 执行主上下文 |
| L2 | `commitments` | ~0.5KB/条，只保留 open + 近 30 天 closed | 派活、提醒、监督 |
| L3 | `founderProfile` | ~2KB 总计 | 风格与偏好 |
| L4 | `artifacts` + `tasks` | 已有 | 产出与进度 |

**不默认做：** 全库向量检索、无上限 chat memory、Agent 群聊记忆。

---

## 4. 分 Phase 迭代路线

### 总览

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
 稳基         可靠CEO      内审打回      文件ingress   懂风格       主动流程
(1周)       (2–3周)      (2–3周)       (2周)        (1–2周)      (2–3周)
```

每 Phase **独立可验收**；未验收不进入下一 Phase。

---

### Phase 0：稳基（Stabilize）— 不改产品行为，只修地基

**目标：** 消除已知 P0/P1 工程风险，为后续编排扩展腾空间。

| 任务 | 改动点 | 验收 |
|------|--------|------|
| 0.1 消除循环 import | `plan_should_dispatch` 抽到 `dispatch_rules.py` 或 lazy import 统一 | `pytest` 全绿；`import engine` 不报错 |
| 0.2 Workflow 可观测 | `ceo.py` / `engine` 结构化 log；`meta.lastWorkflowRun` | 派活失败可在 log / meta 看到 reason |
| 0.3 项目解析回归 | `resolve_project_id` + 测试 | NDA 追问 → `lead-华为` |
| 0.4 服务重启约定 | README / start.sh 注明改 orchestrator 需重启 | 文档 |

**接口：** 无 breaking change。  
**风险：** 低。

---

### Phase 1：可靠 CEO（Understand → Dispatch → Commit）

**目标：** 根治「说了不干」；支持承诺与提醒；**G1、G3、G4 部分**。

#### 1.1 数据模型（dashboard JSON 增域）

```json
{
  "commitments": [
    {
      "id": "cmt-xxx",
      "projectId": "lead-华为",
      "what": "法务重拟双向 NDA",
      "ownerRole": "legal",
      "kind": "deliverable",
      "status": "open",
      "dueAt": "2026-05-21T18:00:00+08:00",
      "linkedTaskId": "task-legal-xxx",
      "linkedArtifactId": "art-nda-xxx",
      "source": "ceo_turn:thread-xxx",
      "createdAt": "...",
      "closedAt": null
    }
  ],
  "projectBriefs": {
    "lead-华为": {
      "clientName": "华为",
      "cooperationMode": "project",
      "ndaType": "mutual",
      "openQuestions": [],
      "confirmedFacts": ["双向保密", "项目合作"],
      "updatedAt": "..."
    }
  }
}
```

#### 1.2 CEO 统一回合（核心）

**现状：**

```
run_chat_phase → ceo_brief_reply (LLM #1)
run_plan_and_workflow_phase → plan_dispatch (LLM #2)
```

**目标：**

```
run_ceo_turn → ceo_structured_turn (LLM #1, JSON)
  → persist reply + briefDelta + commitments + dispatch
  → run_workflow_phase (无第二次「是否派活」LLM)
```

**新增模块建议：**

| 模块 | 路径 | 职责 |
|------|------|------|
| `CeoTurnResult` | `orchestrator/ceo_turn.py` | 解析/校验结构化输出 |
| `commitment_service` | `services/commitments.py` | CRUD、关闭、逾期扫描 |
| `project_brief_service` | `services/project_briefs.py` | merge briefDelta |

**LLM 输出 schema（示意）：**

```json
{
  "reply": "给 Founder 的自然语言",
  "projectId": "lead-华为",
  "briefDelta": { "ndaType": "mutual", "openQuestions": [] },
  "commitments": [
    { "action": "open", "what": "...", "ownerRole": "legal", "dueAt": "..." }
  ],
  "dispatch": {
    "shouldDispatch": true,
    "tasks": [{ "role": "legal", "title": "...", "kind": "nda" }]
  }
}
```

**降级：** LLM 不可用 → 现有 `directives` + `_plan_from_rules` + template fallback。

#### 1.3 提醒与 cue（轻量 Scheduler）

| 机制 | 实现 |
|------|------|
| 承诺到期 | `APScheduler` 或 startup 定时扫 `commitments.dueAt` |
| 产出 | inbox `category: reminder` + 可选 CEO thread 一条 decision |
| Task 失败 | `complete_task` 失败时打开/更新 commitment |

#### 1.4 API / 前端（最小）

| 变更 | 说明 |
|------|------|
| `GET /dashboard` | 含 `commitments` · `projectBriefs` |
| `GET /api/v1/commitments?status=open` | 可选独立读 |
| 收件箱 UI | 增「待跟进」过滤 |
| CEO 对话 | 展示 open commitments 摘要（可选） |

#### 1.5 验收场景（必须全过）

1. 「和华为双向 NDA」→ 更新 brief + 派 legal + commitment open  
2. 「NDA 没更新」→ 再派 + 不关联错项目  
3. CEO 回复含 deadline → commitment 有 `dueAt`，到期 inbox 提醒  
4. 法务 task 完成 → commitment closed，artifact 版本 bump  
5. LLM 超时 → template 兜底 + commitment 仍 open 直至产出  

**版本建议：** v0.4.0  
**风险：** CEO 结构化 JSON 解析失败 → 需 robust parse + 规则兜底（已有经验）

---

### Phase 2：CEO 内审与打回（Review Loop）— **G5、G6** ⚠️

> **实现状态（2026-05）：** `ceo_review.py` + 规则 validator + revision 环 ✅；**LLM 评审层未接**（`ceoReviewScore` 为规则分）。完整 LLM Review → [DEV-STATUS AG-3](./DEV-STATUS.md#32-p0--agent-可演示)。

**目标：** CEO 审员工产出，不合格自动重派，合格后再交 Founder。

#### 2.1 流程

```
Runner 完成 artifact
  → CEO Review (LLM + validator + projectBrief + founderProfile)
      score < threshold  OR  CEO 判 fail
        → artifact.status = "revision"
        → reviewNotes[] 写入
        → dispatch 同 role 修订 Task（带 reviewNotes 作 briefContext）
        → commitment 保持 open
      pass
        → maybe_submit_artifact_review → Founder HITL
        → inbox 通知 Founder
```

#### 2.2 数据扩展

```json
{
  "artifacts": [{
    "status": "draft | revision | review | approved",
    "reviewNotes": [
      { "by": "ceo", "at": "...", "note": "...", "round": 1 }
    ],
    "ceoReviewScore": 72,
    "maxRevisionRounds": 2
  }]
}
```

#### 2.3 编排改动

| 模块 | 改动 |
|------|------|
| `engine._execute_runner` | 完成后调用 `ceo_review_artifact()` |
| `services/ceo_review.py` | 新建：LLM 评审 + 规则叠加 |
| `artifact_workflow` | 区分 `HITL-Founder` vs `Review-CEO` |
| `dispatcher` | `dispatch_revision_task(parentTaskId, notes)` |

#### 2.4 与现有 HITL 关系

```
员工 → CEO Review (自动，可多轮)
     → Founder HITL (你批，现有 hitlQueue)
```

**不替代** Founder HITL；CEO 内审是 **HITL 之前** 的质量门。

#### 2.5 验收场景

1. 法务交粗糙 NDA → CEO 打回 → 修订 Task → v0.3 内容改善 → 再审 pass → 进你 inbox  
2. **2 轮**仍不合格 → Escalate：CEO thread 请示你（**已确认：最多 2 轮打回**）  
3. `reject_artifact`（你驳回）→ 触发 CEO 修订环，而非仅改 draft  

**版本建议：** v0.5.0  
**风险：** 修订环 token 成本 → `maxRevisionRounds=2` + 预算检查（`cost_recorder`）

---

### Phase 3：文件与纪要 Ingress — **G2**

**目标：** CEO 对话可接收附件；纪要解析进 brief + commitments。

#### 3.1 API

```
POST /api/v1/ceo/brief
  Content-Type: multipart/form-data
  fields: text, projectId?, files[]
```

或分步：

```
POST /api/v1/ingress/attachments  → attachmentId
POST /api/v1/ceo/brief  { text, attachmentIds: [] }
```

#### 3.2 存储

```
data/uploads/{uuid}/original.pdf
data/uploads/{uuid}/extracted.md   # 解析结果
dashboard.attachments[]            # 索引
```

#### 3.3 解析管线

| 类型 | 处理 |
|------|------|
| `.md` | 直读 |
| `.pdf` | `pypdf` 提取文本（Phase 3 必做；扫描件后续可选 OCR/vision） |
| 输出 | `IngressDocument` → CEO Turn 输入 |

> **已确认：** Phase 3 首版仅 **Markdown + PDF**；`.docx` / `.txt` 后置。

#### 3.4 CEO Turn 输入扩展

```
Founder 说：{text}
附件摘要：{extractedSummary}
附件待办：{extractedActionItems}
```

#### 3.5 验收

1. 上传会议纪要 md → CEO 提取「华为 NDA 双向」→ 更新 brief + 派活  
2. 附件过大 → 413 + 友好错误  

**版本建议：** v0.6.0  
**风险：** 解析质量不稳定 → CEO reply 中列出「我理解到的要点，请确认」

---

### Phase 4：Founder Profile（懂你的风格）— **G7**

**目标：** 轻量偏好，不臃肿。

#### 4.1 数据

```json
{
  "founderProfile": {
    "communication": { "preferConcise": true, "maxReplySentences": 8 },
    "deliverables": {
      "legal": { "preferMutualNdaTemplate": true, "rejectBulletDraft": true }
    },
    "escalation": { "alwaysHitlFor": ["contract", "sow"] },
    "learnedNotes": [
      { "at": "...", "note": "Founder 强调 NDA 必须双向", "source": "thread-xxx" }
    ]
  }
}
```

#### 4.2 写入策略

| 来源 | 方式 |
|------|------|
| 设置页 | `PUT /founder/profile` 显式编辑 |
| CEO Turn | `profileDelta` → **inbox 建议**，Founder 确认后才写入 |
| 你驳回 HITL | 生成 **profile 建议**（同上，不自动写入） |

#### 4.3 使用点

- CEO Turn system prompt 注入 profile 摘要  
- CEO Review 阈值/检查项按 profile 调整  

**版本建议：** v0.7.0  
**已确认：** Profile **仅 Founder 确认后写入**；inbox 展示「CEO 建议记住：…」一键采纳/忽略

---

### Phase 5：主动流程推进（Process Cue）— **G4、G8**

**目标：** CEO 按项目 stage + open commitments + openQuestions 主动 push。

#### 5.1 流程引擎收敛

| 现状 | 目标 |
|------|------|
| `transitions.py` 散落规则 | `workflow_engine.py` 读 `workflow_templates` + project.stage |
| kickoff / HITL 硬编码 | 事件：`artifact.approved` → 查转移表 → 下一 Dispatch |

#### 5.2 主动 cue 来源

| 触发 | 动作 |
|------|------|
| `projectBrief.openQuestions` 非空 | inbox：「可口可乐还缺 2 项信息」 |
| stage=clarify 且无 PRD | CEO 建议下一步 |
| commitment 逾期 | 提醒 + 可选自动重派 |
| HITL 通过 | 按转移表 Dispatch 下一角色 |

#### 5.3 验收

华为 NDA 完成后，CEO 主动 cue：「NDA 已定稿，是否推进 PRD / 立项评估？」

**版本建议：** v0.8.0  
**风险：** 过于主动 → `cueFrequency` 配置 + 勿扰时段

---

### Phase 6：设置平台 & Skill Hub（执行面）

**目标：** 设置页 IA（系统 / 角色）；`roleRegistry` 动态扩展（**设置页手动新增 role，不预置 brand mock**）；Skill Hub + Tool Registry + MCP + 多 Model；CEO 驱动 Skill 安装（Founder 发 SKILL → CEO 提案 → Ops 采纳）。

| 文档 | 内容 |
|------|------|
| [SETTINGS-PLATFORM-ROADMAP.md](./SETTINGS-PLATFORM-ROADMAP.md) | Epic 1–5 总路线 |
| [SETTINGS-V2.md](./SETTINGS-V2.md) | 设置 UI / 数据 / API |
| [SKILL-HUB.md](./SKILL-HUB.md) | Skill / Tool / MCP / Router / 链 |

| Epic | 交付 |
|------|------|
| 1 | `settings.js`；系统/角色 segment；`POST /roles/registry` |
| 2 | Tool Registry + Runner enforce |
| 3 | Skill Hub + import + inbox `skill_proposal` |
| 4 | MCP Bridge + image/video slot |
| 5 | Skill 链（v1 单 skill，架构预留） |

**版本建议：** v0.9.x 起按 Epic 发布

---

## 5. 模块与文件映射（规划期）

```
backend/app/
├── orchestrator/
│   ├── engine.py              # 逐步变薄，委托 ceo_turn / supervisor / review
│   ├── ceo_turn.py            # Phase 1 新建
│   ├── ceo_review.py          # Phase 2 新建
│   ├── supervisor.py          # Phase 1–2 承诺/Task 监督
│   ├── workflow_engine.py     # Phase 5 收敛转移表
│   ├── dispatch_planner.py    # Phase 1 降级为 fallback
│   └── directives.py          # 规则兜底保留
├── services/
│   ├── commitments.py         # Phase 1
│   ├── project_briefs.py      # Phase 1
│   ├── founder_profile.py     # Phase 4
│   ├── ingress_documents.py   # Phase 3
│   └── scheduler.py           # Phase 1 提醒
├── api/
│   ├── ceo.py                 # Phase 1 扩展；Phase 3 multipart
│   ├── commitments.py         # Phase 1 可选
│   └── founder.py               # Phase 4
└── models/
    └── commitments.py         # Phase 3+ 可选迁 SQL
```

---

## 6. 接口演进清单（汇总）

| Phase | 方法 | 路径 | 说明 |
|-------|------|------|------|
| 0 | — | — | 无新接口 |
| 1 | GET | `/commitments` | open / overdue 列表 |
| 1 | PATCH | `/commitments/{id}` | 手动关闭 / 改 due |
| 1 | — | `GET /dashboard` | +commitments, +projectBriefs |
| 1 | — | `POST /ceo/brief` | 响应 meta 含 dispatchSummary |
| 2 | POST | `/artifacts/{id}/ceo-review` | 手动触发内审（调试） |
| 2 | — | artifacts | +reviewNotes, status=revision |
| 3 | POST | `/ceo/brief` | multipart |
| 3 | POST | `/ingress/attachments` | 可选 |
| 4 | GET/PUT | `/founder/profile` | 偏好读写 |
| 5 | GET | `/projects/{id}/next-steps` | 流程 cue 只读 |

**兼容原则：** 旧前端不读新域不影响；新 UI 渐进启用。

---

## 7. 测试策略

| 层级 | Phase 1+ 要求 |
|------|----------------|
| 单元 | `resolve_project_id` · `commitments` · `ceo_turn` parse · `directives` |
| 集成 | `POST /ceo/brief` → task + commitment + artifact 全链 |
| 场景 | 本文 §4 各 Phase 验收场景 → `tests/scenarios/test_huawei_nda.py` |
| 回归 | 现有 50+ tests 不删 |

**不建议：** 依赖 live LLM 的 CI；LLM mock + 规则 fallback 测编排。

---

## 8. Founder 决策（已锁定 · 2026-05-21）

| # | 决策 | 结论 |
|---|------|------|
| **D1** | Phase 1 合并 CEO 双 LLM | ✅ **一次结构化回合**（reply + dispatch + commitments 同源） |
| **D2** | commitments 存储 | ✅ **先 dashboard JSON**，量大再迁 SQL |
| **D3** | CEO 内审最大修订轮次 | ✅ **2 轮**，仍不合格 → Escalate Founder |
| **D4** | 附件格式 | ✅ Phase 3 首版 **Markdown + PDF** |
| **D5** | Profile 学习 | ✅ **仅 Founder 确认后写入**（inbox 建议 + 一键采纳） |
| **D6** | 主动 cue | ✅ **逾期即时提醒 + 其余每日摘要** |

---

## 9. 建议的迭代节奏（执行顺序）

```
Week 1   Phase 0 稳基 + Phase 1 设计评审（本文确认）
Week 2–3 Phase 1 实现 + 华为 NDA 垂直验收
Week 4–5 Phase 2 CEO Review Loop + NDA 打回演示
Week 6   Phase 3 附件（md + PDF）+ 纪要场景
Week 7   Phase 4 Profile 设置页
Week 8+  Phase 5 流程引擎 + 主动 cue
```

**垂直切片（贯穿 Phase 1–2 的 Demo 故事线）：**

> 华为线索 → 你确认双向 NDA → CEO 承诺 + commitment → 法务产出 → CEO 打回 → 修订 → 合格 → 进你 inbox 批准 → 工作室 v1.0 定稿

此故事线跑通 = 核心编排可信，再扩展可口可乐/立项等横向场景。

---

## 10. 明确不做（本规划周期内）

- Agent 自由群聊 / Multi-Agent GroupChat  
- 全量 chat 向量 memory / RAG 知识库  
- 替换现有 HITL 为全自动（你仍是最终签字人）  
- 微服务拆分 / 消息队列 / Docker 必选  
- 第一版就接个人微信  

---

## 11. 与现有文档的关系

| 文档 | 关系 |
|------|------|
| AGENTS.md | 本规划 **细化 Phase 3e+**，不违背星型调度 |
| API.md | Phase 完成后回写 §5 新端点 |
| IMPLEMENTATION.md | 可并入 Milestone Phase 3.1–3.5 |
| PRD.md | G1–G8 可作为 Phase 4+ PRD 验收附录 |

---

## 12. 下一步（执行）

1. ~~Founder 确认 D1–D6~~ ✅ 已完成  
2. **Phase 0** 稳基（循环 import、workflow telemetry、回归测试）  
3. **Phase 1** 开干：先写 `tests/scenarios/test_huawei_nda.py`（红灯）→ `ceo_turn.py` + `commitments` + `project_briefs`  
4. 垂直验收：华为 NDA 承诺 → 派活 → 提醒 → 产出（v0.4.0）  

> 实现前建议开分支 `feat/ceo-turn-v0.4`；是否现在开工由 Founder 一句话触发。

---

*文档维护：每 Phase 结束时更新 §2 基线与 §9 节奏。*
