# OPC Agent 集群 · 产品需求文档（PRD）

| 项 | 内容 |
|----|------|
| 版本 | v0.3 已确认 · Mock 看板全功能 |
| 状态 | Phase 1 完成 · **Phase 2 后端设计草案** |
| 读者 | Founder（你）、后续开发 |
| 关联 | [业务全景 HTML](../architecture.html) · [后端设计 BACKEND.md](./BACKEND.md) |

---

## 1. 产品定位

### 1.1 是什么

一套 **一人公司（OPC）内部 Agent 运营系统**。你是对外唯一门面；对内通过 **Web 看板** 管理五个 Agent（CEO + 产品 / 法务 / 开发 / 运营），像带一支小团队一样掌握「谁在干什么、卡在哪、每个项目赚不赚钱」。

### 1.2 不是什么

- ❌ 传统 BI / 数据看板（图表、KPI 大屏）
- ❌ 给客户用的门户
- ❌ Cursor / IDE 插件
- ❌ 第一版就接真实 LLM（Phase 1 仅 Mock；**Phase 2 接 API，Phase 3 接 Agent**）
- ❌ 独立移动端 H5（飞书/企微作为渠道，不做单独移动页）

### 1.3 Phase 1 目标（已完成）

> **用静态 Mock 跑通完整看板交互**，验证「一人公司带 Agent 团队」的管理体验。

成功标准（均已达成）：

- [x] 打开看板 3 秒内理解五角色在忙什么
- [x] 点击角色可看 running / pending + 活动流
- [x] Mock 覆盖 2 并行项目 + 线索 + 1 待 HITL + 1 已交付
- [x] 项目工作室、收件箱、经营、客户、周报、结项流程可演示
- [x] 主观感受：像在带团队，不像看数据库表

### 1.4 Phase 2 目标（下一步）

> **FastAPI + SQLite + 本地项目目录**，前端改读 API；详见 [BACKEND.md](./BACKEND.md)。

- [ ] 按项目本地存档产出物（文件系统 + DB 索引）
- [ ] 飞书 / 企业微信对话接入 CEO 中枢
- [ ] 五角色独立 API Base URL + API Key 配置
- [ ] Token 成本自动记账 → 项目盈亏
- [ ] Docker 单容器部署 + 数据卷备份

---

## 2. 用户与场景

### 2.1 唯一用户

**Founder（你）** — 获客、传需求给 CEO、HITL 审批、对外交付。

### 2.2 核心场景

| # | 场景 | 你想看到什么 |
|---|------|--------------|
| S1 | 早晨打开看板 | 各角色整体状态 + 今天在跑哪些项目 |
| S2 | 某角色好像卡住了 | 点进角色 → 看 running task 的阻塞原因、在等谁 |
| S3 | 有新客户需求 | 通过 CEO 输入区登记（Mock 阶段可按钮模拟）→ 看 Pipeline 变化 |
| S4 | 有待审批事项 | 「待你批」入口醒目 → 跳 HITL 详情 |
| S5 | 周会前复盘 | CEO 一页纸周报 + Pipeline / 待决 / 经营快照 |
| S6 | 看项目是否赚钱 | **经营 Tab** → 项目盈亏（工作室 v2 不再展示 P&L） |
| S7 | 结项交付 | HITL-3 批准 → 结项清单 → 导出客户 ZIP |

---

## 3. 信息架构（IA · v0.3 已实现）

```
看板 App（Tab 导航）
├── 概览          脉搏条 + 五角色节点 + 协作连线 → 点击弹窗（任务/活动流）
├── 项目          Pipeline 统计 + 项目卡片（含 P&L 摘要）→ 项目工作室 Sheet
├── 客户          客户档案、关联项目、纪要、收款
├── 收件箱        必读 / 请示 / 待批 · 待办·已办·归档 · HITL 批准/驳回
├── 经营          收入 / Token 成本 / 毛利 / 项目盈亏 / 按角色·周
├── 周报          CEO 一页纸（Pipeline·待决·经营快照·五部门摘要）
├── 设置          系统设置（Founder/编排/Skill Hub/MCP）+ 角色设置（身份/Profile/多模型/Skill 绑定）→ 见 `SETTINGS-PLATFORM-ROADMAP.md`
└── CEO FAB       简报投递 + 对话线程 + 渠道状态 + 周报入口
```

**导航原则：**

- **A 为主** — 按项目进工作室看产出物
- **C 为辅** — CEO 推送到收件箱（必读 / 请示 / 待批）
- **经营** — 确保每个项目赚钱，不是只看公司总账

**项目工作室（Sheet · v2）：**

- 顶栏：客户名 · 阶段 · 进度% · HITL 提示 · **项目 ↓**（ZIP 下载）
- 左：阶段分组 + 交付状态点 + 折叠 Brief / 会诊 / 结项
- 中：**当前焦点条（1 条）** → 交付标题 + **交付 ↓** + 操作条 + Viewer
- 盈亏 → **经营 Tab**；批量 HITL → **收件箱**

详见 [WORKROOM-V2.md](./WORKROOM-V2.md)。

---

## 3.1 信息架构（历史 · L0/L1 模型）

> 早期 PRD 用 L0 舰队 / L1 角色详情两层描述，v0.3 改为 **Tab + 弹窗/Sheet**，信息等价、交互更轻。

---

## 4. L0 · 角色舰队页（首页）

### 4.1 公司脉搏条（顶部）

| 字段 | 示例 | 说明 |
|------|------|------|
| 进行中项目 | 2 | 阶段 3–4 的项目数 |
| 待你审批 | 1 | HITL 未处理数，可点击 |
| 告警 | 1 | 超期 / 阻塞 / 高风险，CEO 升级 |
| 本周活跃线索 | 5 | 运营 Pipeline 快照 |

### 4.2 六角色状态卡（核心）

**布局：** 桌面 3×2 网格；移动 单列。CEO 卡可略大或置顶强调「主接口」。

每张 **角色卡** 必含：

| 字段 | 类型 | 示例 | 「管人」意图 |
|------|------|------|--------------|
| 角色名 + 职能 | 文本 | CEO · 调度与立项 | 知道这是谁 |
| **工作状态** | 枚举 | 工作中 / 空闲 / 等待中 / 阻塞 | 像看员工在不在工位 |
| **当前负荷** | 数值 | 2/3 任务槽 | 是否过载 |
| **当前聚焦** | 一行 | 评估 Acme 立项风险 | 此刻在干什么 |
| **关联项目** | 标签 | Acme · Beta | 业务上下文 |
| Running 数 | 徽章 | ● 1 | 正在执行 |
| Pending 数 | 徽章 | ○ 3 | 排队待做 |
| 上次活跃 | 相对时间 | 3 分钟前 | 是否「摸鱼」/ 僵死 |
| 状态色条 | 颜色 | 绿/黄/红 | 一眼健康度 |

**工作状态枚举（全角色统一）：**

| 状态 | 含义 | 色 |
|------|------|-----|
| `idle` 空闲 | 无 running task，可接新活 | 灰 |
| `working` 工作中 | 有 running task | 绿 |
| `waiting` 等待中 | 等 Founder HITL / 等其他角色 | 黄 |
| `blocked` 阻塞 | 异常、缺信息、技术卡点 | 红 |

### 4.3 Pipeline 快照（运营）

横向五列（与 v3 业务全景一致）：线索池 · 待澄清 · 进行中 · 待你审批 · 已交付/搁置。

每列 1–3 张线索卡：客户名、一句话需求、优先级 P1/P2/P3、负责人项目阶段。

**Founder 必看** — 默认展开；可折叠。

### 4.4 快捷操作（Mock 阶段）

- **向 CEO 传达需求** — 打开输入框（Mock：写入本地 state，刷新 Pipeline）
- **待你审批** — 列表跳转 HITL 卡片（Mock：批准/驳回按钮）

---

## 5. L1 · 角色详情页

点击 L0 某角色卡进入。顶部面包屑：`舰队 > CEO`。

### 5.1 角色档案头

| 字段 | 说明 |
|------|------|
| 角色名 + Charter 一句话 | 如：开发 · 方案、PoC、交付物 |
| 当前工作状态 | 同 L0 |
| 负荷 | 2/3 |
| 当前关联项目 | 可多选 |
| 「汇报给 CEO / 你」关系 | 小字说明汇报链 |

### 5.2 正在执行（Running Tasks）

任务卡必含：

| 字段 | 示例 |
|------|------|
| 任务标题 | 撰写 Acme 项目 PRD |
| 所属项目 | Acme 科技 · 内部审批流 |
| 业务阶段 | 阶段 3 · 方案签约 |
| 开始时间 | 今天 09:32 |
| 已耗时 | 1h 20m |
| 进度描述 | 已完成背景与目标，正在写验收标准 |
| 进度条 | 60%（Mock 可人工填） |
| 阻塞/等待 | 无 / 等 Founder 确认范围 |
| 预计完成 | 今天 18:00 |
| 产出物链接 | `clients/acme/handoffs/prd-draft.md`（Mock #） |

### 5.3 待执行队列（Pending Tasks）

按 **优先级** 排序。字段：

| 字段 | 说明 |
|------|------|
| 优先级 | P0 / P1 / P2 |
| 任务标题 | |
| 所属项目 | |
| 前置依赖 | 如：待 HITL-1 通过 |
| 预计工时 | 2h（Mock） |
| 计划开始 | 今天下午 |

### 5.4 等待中（Waiting / Blocked）

单独分区，避免与 Pending 混淆：

| 类型 | 含义 | 示例 |
|------|------|------|
| `waiting_founder` | 等你审批 | HITL-2 报价待批 |
| `waiting_role` | 等另一 Agent | 等产品 PRD 完成 |
| `blocked` | 异常 | 缺客户数据样本 |

### 5.5 最近完成（Recent Done · 7 天内）

- 任务名、完成时间、产出物、一句话结果

### 5.6 活动流（Activity Timeline）

按时间倒序：

```
10:32  开始任务「撰写 Acme PRD」
10:45  产出章节：背景与目标
11:02  等待 Founder 确认范围（HITL-1）
11:20  HITL-1 已通过（Mock）
```

**「管人」感来自：** 有时间线、有等待原因、有产出片段，不是只有 task_id。

---

## 6. 角色专属展示字段（L1 增强）

在通用 task 字段之上，每角色增加 **职能上下文**：

### CEO

| 额外字段 | 示例 |
|----------|------|
| 待决策队列 | Acme 接不接 · Beta scope 变更 |
| 风险告警 | Beta 项目超预算 20% |
| 今日汇报摘要 | 已汇总 4 角色状态 |

### 产品

| 额外字段 | 示例 |
|----------|------|
| 当前 PRD 完成度 | 3/5 章节 |
| 待澄清问题数 | 2 条待你找客户确认 |

### 财务法务

| 额外字段 | 示例 |
|----------|------|
| 待出报价 | 1 份 |
| 合规标记 | Acme 涉 PII · 需深审 |

### 开发

| 额外字段 | 示例 |
|----------|------|
| 环境 | local / staging |
| 自测状态 | 3/5 通过 |
| Token 用量（Mock） | 12.4k |

### 运营

| 额外字段 | 示例 |
|----------|------|
| Pipeline 变更 | 本周 +2 线索 |
| 草稿待审 | 1 封客户进度邮件 |

---

## 7. Mock 数据模型（Phase 1）

```typescript
// 逻辑 schema，Phase 1 用 JSON 文件即可

type RoleId = "ceo" | "product" | "legal" | "dev" | "ops";

type WorkStatus = "idle" | "working" | "waiting" | "blocked";

type TaskStatus = "running" | "pending" | "waiting" | "blocked" | "done";

interface RoleSnapshot {
  id: RoleId;
  name: string;
  charter: string;
  workStatus: WorkStatus;
  load: { current: number; max: number };
  focus: string;                    // 当前聚焦一行话
  projectIds: string[];
  runningCount: number;
  pendingCount: number;
  lastActiveAt: string;             // ISO
  extras: Record<string, unknown>;  // 角色专属字段
}

interface Task {
  id: string;
  roleId: RoleId;
  title: string;
  projectId: string;
  stage: string;                    // 阶段1-5
  status: TaskStatus;
  priority?: "P0" | "P1" | "P2";
  startedAt?: string;
  elapsed?: string;
  progress?: number;                // 0-100
  progressNote?: string;
  blockedReason?: string;
  waitingOn?: "founder" | RoleId;
  dueAt?: string;
  outputRef?: string;
  dependsOn?: string[];             // task ids
  activities: Activity[];
}

interface Activity {
  at: string;
  message: string;
}

interface Project {
  id: string;
  clientName: string;
  summary: string;
  pipelineColumn: "lead" | "clarify" | "active" | "hitl" | "done";
  priority: "P1" | "P2" | "P3";
  stage: string;
  hitlPending?: "HITL-1" | "HITL-2" | "HITL-3" | "HITL-4";
}

interface DashboardMock {
  pulse: { activeProjects: number; hitlPending: number; alerts: number; leads: number };
  roles: RoleSnapshot[];
  tasks: Task[];
  projects: Project[];
  hitlQueue: HitlItem[];
}
```

**Mock 文件位置（建议）：**

```
opc-agent-framework/
├── mock/
│   └── dashboard.json      # 完整 Mock 数据集
├── dashboards/
│   └── app/                # Phase 1 看板前端
└── docs/
    └── PRD.md              # 本文档
```

---

## 8. Mock 数据集要求（至少）

| 实体 | 数量 | 要求 |
|------|------|------|
| 项目 | ≥2 进行中 + ≥2 线索 | 覆盖不同阶段 |
| Running tasks | 每角色 0–2 | CEO/开发非 idle |
| Pending tasks | 每角色 1–3 | 有依赖关系 |
| Waiting/Blocked | ≥2 | 一个等你 HITL，一个跨角色等待 |
| HITL 队列 | ≥1 | 可 Mock 批准 |
| Activity | 每 running task ≥3 条 | 时间线可读 |

**建议 Mock 故事线：**

1. **Acme 科技 · 内部审批流** — 阶段 4，开发 running，HITL-3 待批  
2. **Beta 贸易 · 发票记账** — 阶段 2，CEO 评估风险，产品 pending  
3. **线索：某餐饮连锁** — 线索池，运营已登记  

---

## 9. 非功能需求

| 项 | Phase 1 Mock |
|----|--------------|
| 性能 | 本地打开 <1s |
| 部署 | 静态文件 + `python -m http.server` 即可 |
| 技术栈 | HTML + CSS + 原生 JS 读 JSON（或 Vite+Vue 若需组件化） |
| 响应式 | 桌面优先，手机可浏览 |
| 实时 | Mock 阶段不需要 SSE；Phase 2 再接 |
| 语言 | 中文 UI |

---

## 10. 分期路线

| 阶段 | 交付 | 技术 |
|------|------|------|
| **Phase 1** | Mock 看板 v0.3（全 Tab） | HTML + CSS + JS + `mock/dashboard.json` |
| **Phase 2a** | API 骨架 + SQLite + 静态托管 | FastAPI + Docker · [BACKEND.md](./BACKEND.md) |
| **Phase 2b–e** | 项目文件存储 / inbox / 渠道 / 角色配置 | 同上 |
| **Phase 3** | 真实 Agent Runner | LLM + 工作流，写 task / token_runs |

**启动方式（Phase 1）：** `./start.sh` → `http://localhost:8765/dashboards/app/`

---

## 11. 明确不做（Phase 1）

- 真实 LLM 调用
- 用户登录 / 多租户
- 传统图表大屏（折线、饼图可 Phase 2+ 作为辅助，不作主视图）
- 客户-facing 界面

---

## 12. Founder 确认记录（2026-05-21）

- [x] L0 / L1 两层信息架构 — 确认
- [x] 角色卡增加：头像、职位、部门、本周工时
- [x] Pipeline — **独立 Tab**（不在舰队页默认展开）
- [x] Phase 1b — 纯 HTML + CSS + JS，暂不接后端
- [x] Mock 场景 — Agent 可交付需求（审批流、发票 OCR、对账、合同审阅）

**已交付：** `mock/dashboard.json` · `dashboards/app/` · `assets/avatars/`

---

## 附录 A · 线框示意（L0）

```
┌──────────────────────────────────────────────────────────────────┐
│ 脉搏：进行中 2 · 待审批 1 · 告警 1 · 线索 5    [向CEO传达] [待批] │
├──────────────────────────────────────────────────────────────────┤
│ ┌──────── CEO ────────┐ ┌──── 产品 ─────┐ ┌──── 法务 ─────┐     │
│ │ 🟢 工作中  负荷 2/3  │ │ 🟢 工作中      │ │ ⚪ 空闲        │     │
│ │ 评估 Beta 立项风险   │ │ 写 Acme PRD   │ │ 无进行中       │     │
│ │ Acme · Beta         │ │ Acme          │ │ ○2 待办        │     │
│ │ ●1 ○2 · 3分钟前      │ │ ●1 ○1         │ │               │     │
│ └─────────────────────┘ └───────────────┘ └───────────────┘     │
│ ┌──── 开发 ─────┐ ┌──── 运营 ─────────────┐                      │
│ │ 🟡 等待 HITL-3 │ │ 🟢 工作中  负荷 3/3    │                      │
│ │ Acme 交付物    │ │ 维护 Pipeline         │                      │
│ └───────────────┘ └───────────────────────┘                      │
├──────────────────────────────────────────────────────────────────┤
│ Pipeline：线索池(2) │ 待澄清(1) │ 进行中(2) │ 待你批(1) │ 已交付  │
└──────────────────────────────────────────────────────────────────┘
```

## 附录 B · 线框示意（L1 · 点进「产品」）

```
舰队 > 产品 Agent
────────────────────────────────────────
产品 · 需求与 PRD          🟢 工作中  负荷 1/2
当前项目：Acme 科技
────────────────────────────────────────
▶ 正在执行
  ┌ 撰写 Acme PRD ─────────────────── 60%
  │ 阶段3 · 开始 09:32 · 已用 1h20m
  │ 进度：背景与目标已完成，写验收标准中
  │ 产出：clients/acme/handoffs/prd-draft.md
  └────────────────────────────────────
▶ 待执行
  · [P1] Beta 需求结构化（依赖 CEO 立项）
▶ 等待中
  · （无）
▶ 最近完成
  · 昨天：Gamma 项目 PRD v1 已定稿
▶ 活动流
  10:32 开始 Acme PRD
  10:45 完成章节：背景与目标
  ...
```

---

## 13. v0.2 增量（已采纳 · 已实现 Mock）

### 信息架构

| Tab / 入口 | 职责 |
|------------|------|
| 概览 | 团队状态 + 协作连线（不变） |
| 项目 | 统计 + 项目卡片 → **进入工作室** |
| 收件箱 | **C 必读** + 请示 + **待批（HITL）** |
| CEO FAB | 简报投递 + 对话线程 + **渠道状态** |

### A · 项目工作室（v2）

- 点项目 → 全屏 Sheet
- 顶栏：阶段 · 进度 · **项目 ↓**
- 左：阶段分组 + 折叠 Brief / 会诊 / 结项
- 中：焦点条 + 交付操作 + Viewer

详见 [WORKROOM-V2.md](./WORKROOM-V2.md)。

### C · 收件箱

- CEO 推送必读项（如「先读 PRD 再批交付物」）
- 请示类：同意 PoC / 再议
- 待批类：全文 + 驳回意见 + 批准

### 移动端 · 飞书 / 微信（Phase 2 架构）

```
Founder 手机（飞书/企微）
    ↕ Webhook / Bot
CEO Agent 中枢
    ↕ 同步
Web 看板（CEO FAB + 收件箱）
```

- Mock 已展示：消息 `channel: feishu | wechat | web`
- Phase 2：飞书 Bot 收消息 → 写 `ceoThread` → 推收件箱；CEO 回复反向推送

## 14. Founder 确认记录（2026-05-21 v0.2）

- [x] A 项目工作室 + C 收件箱
- [x] 合并审批进收件箱
- [x] CEO FAB + 简报投递
- [x] 飞书/微信渠道纳入设计（Mock 状态展示）
- [x] 保持 Apple 玻璃视觉风格

---

## 15. v0.3 增量（2026-05 · 已实现 Mock）

### 新增 Tab / 模块

| 模块 | 功能 |
|------|------|
| **客户** | 客户档案、多项目、沟通纪要、收款记录 |
| **经营** | 公司级收入/成本/毛利 + **项目盈亏**（健康度：盈利/需关注/线索） |
| **周报** | 列表 + 详情 Modal：项目进展 / 风险 / 经营一句 / 展望（见 `WEEKLY-V2.md`） |
| **结项** | 结项清单、HITL-3 后进入结项、客户 ZIP vs 内部 ZIP |

### 增强

| 模块 | 增强 |
|------|------|
| 概览 | 公司脉搏条 + 告警横幅 |
| 角色弹窗 | running/pending 任务卡 + 活动流 + extras |
| 收件箱 | 待办/已办/归档、驳回历史、周报必读入口 |
| 项目卡片 | HITL / 结项状态 / 盈亏一行摘要 |
| 工作室 | 产出 version、Demo 外链、焦点条 + 交付操作（v2 移除顶部 P&L） |

### Mock 数据 v0.3.0

`mock/dashboard.json` 新增/扩展：

- `clients` · `payments` · `closure` · `weeklyReport` · `rolePerformance`
- `costs.byProject` 含 revenue / margin / health
- `rejectHistory` · inbox `status`（active/done/archived）

### 明确不做

- 独立移动端 H5（飞书/企微作渠道即可）

---

## 16. Phase 2 后端需求（Founder 确认项）

详见 **[docs/BACKEND.md](./BACKEND.md)**、**[docs/API.md](./API.md)** 与 **[docs/IMPLEMENTATION.md](./IMPLEMENTATION.md)**，摘要：

| # | 需求 | 方案 |
|---|------|------|
| 1 | 本地按项目存档交付物 | `data/projects/{id}/artifacts/` + SQLite 索引 |
| 2 | 轻量数据库 | SQLite 单文件 `data/opc.db` |
| 3 | 飞书 / 微信对话 | Channel Adapter；**Phase 2 先做飞书**，微信后置 |
| 4 | 角色 URL + API Key | `role_config` 表 + 加密存储 |
| 5 | 易部署、健壮 | **本地 Python + start.sh**；云端/systemd 可选；Docker 非必需 |

---

## 17. Founder 确认记录（v0.3 · 讨论中）

- [x] v0.3 PRD 与当前 Mock 看板一致
- [x] 核心栈：FastAPI + SQLite + 本地 `data/` 目录
- [x] **不用 Docker**（本地 Python + `./start.sh`）
- [x] **不做登录**（本地 127.0.0.1 单用户）
- [x] 云端 **可选**（将来域名 + VPS，非 Phase 2 前提）
- [x] 渠道：**飞书优先**，微信后置
- [x] API 契约 v1.0（Mock JSON = 黄金样本，见 API.md）
- [x] Phase 2 实施计划草案（IMPLEMENTATION.md · 待确认）
- [ ] 确认实施计划后开始 Phase 2a
