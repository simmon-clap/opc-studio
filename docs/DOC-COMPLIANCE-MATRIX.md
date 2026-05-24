# 文档 ↔ 实现 · 符合性对照表

> **SSOT：** [DEV-STATUS.md](./DEV-STATUS.md) — 未完成 backlog 以此为准  
> **基线：** 代码 `v0.9.x` · **160 tests passed** · 对照日期 **2026-05-24（文档已同步）**  
> **图例：** ✅ 符合 · ⚠️ 部分实现/偏离 · ❌ 未实现 · 📋 文档过时 · 🔇 仅参考 · ➖ 明确不做

**统计（规范文档条目合计约 120+ 条）：**

| 符合度 | 数量（约） | 说明 |
|--------|-----------|------|
| ✅ | ~62 | 设计与实现一致 |
| ⚠️ | ~38 | 有代码但 stub/缺 UI/与文档细节不符 |
| ❌ | ~14 | 文档要求、代码无 |
| 📋 | ~8 | 实现已超前，文档未更新 |
| ➖ | ~6 | 文档已否决或后置 |

---

## 0. 文档索引（本表覆盖范围）

| # | 文档 | 性质 | 对照节 |
|---|------|------|--------|
| 0 | [DEV-STATUS.md](DEV-STATUS.md) | **开发状态 SSOT** | §0 |
| 1 | [PRD.md](PRD.md) | 产品需求 | §1 |
| 2 | [BACKEND.md](BACKEND.md) | 后端设计 | §2 |
| 3 | [IMPLEMENTATION.md](IMPLEMENTATION.md) | 实施计划 | §3 |
| 4 | [API.md](API.md) | API 契约 | §4 |
| 5 | [AGENTS.md](AGENTS.md) | 编排设计 | §5 |
| 6 | [AGENTS-COMPARE.md](AGENTS-COMPARE.md) | 选型说明 | §6 |
| 7 | [CEO-ORCHESTRATION-ROADMAP.md](CEO-ORCHESTRATION-ROADMAP.md) | CEO 产品路线 | §7 |
| 8 | [SETTINGS-PLATFORM-ROADMAP.md](SETTINGS-PLATFORM-ROADMAP.md) | 设置平台 Epic | §8 |
| 9 | [SETTINGS-IMPLEMENTATION.md](SETTINGS-IMPLEMENTATION.md) | 设置实现说明 | §9 |
| 10 | [SETTINGS-V2.md](SETTINGS-V2.md) | 设置 IA/UX | §10 |
| 11 | [SKILL-HUB.md](SKILL-HUB.md) | Skill 架构 | §11 |
| 12 | [WORKROOM-V2.md](WORKROOM-V2.md) | 工作室 v2 | §12 |
| 13 | [FINANCE-V2.md](FINANCE-V2.md) | 经营 v2 | §13 |
| 14 | [WEEKLY-V2.md](WEEKLY-V2.md) | 周报 v2 | §14 |
| 15 | [PULSE-AGENCY-SPEC.md](PULSE-AGENCY-SPEC.md) | 运行时 | §15 |
| 16 | [CHANNELS-INTEGRATION.md](CHANNELS-INTEGRATION.md) | 渠道 | §16 |
| 17 | [PRODUCT-COMPLETION-ROADMAP.md](PRODUCT-COMPLETION-ROADMAP.md) | 完善规划 | §17 |
| 18 | [README.md](../README.md) | 仓库说明 | §18 |
| 19 | [deploy/README.md](../deploy/README.md) | 部署 | §19 |
| — | `reference/from-cluster/**` | 🔇 早期原型参考 | §20 |

---

## 1. PRD.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| P1 | Phase 1 Mock 看板全功能 | ✅ | `mock/` + 前端 7 Tab |
| P2 | Phase 2：FastAPI + SQLite + 本地存档 | ✅ | `backend/app` · `data/opc.db` · `ingress_documents` |
| P3 | 按项目本地存档产出物 | ✅ | artifacts + `projects/{id}/export` |
| P4 | 飞书/企微接入 CEO 中枢 | ⚠️ | inbound 骨架；飞书 Webhook **501**；`channels.connected` 仍为 seed |
| P5 | 五角色独立 API Key | ⚠️ | 分槽 text/image/video ✅；文档写「五角色」未要求分能力 |
| P6 | Token 成本 → 项目盈亏 | ✅ | `agent_runs` · `costs.byProject` · `record_agent_cost` |
| P7 | Docker 单容器部署 | ➖ | PRD §17 后置；无 Dockerfile |
| P8 | IA：概览/项目/客户/收件箱/经营/周报/设置 | ✅ | `index.html` + `app.js` |
| P9 | 工作室 v2（焦点条、阶段、无 P&L） | ✅ | `workroom.js` · [WORKROOM-V2](WORKROOM-V2.md) |
| P10 | CEO FAB + 渠道状态 | ⚠️ | FAB ✅；渠道 pill 非真实连接状态 |
| P11 | Phase 1 不接真实 LLM | ✅ | Phase 3 已接 `llm_client`；PRD/README 已同步 |
| P12 | 场景 S1–S7 可演示 | ✅ | 种子 + API 驱动 |
| P13 | 设置：系统+角色（SETTINGS 路线图） | ⚠️ | 主体 ✅；SETTINGS-V2 细项见 §10 |

---

## 2. BACKEND.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| B1 | FastAPI + SQLite + httpx | ✅ | `main.py` · `db.py` · `llm_client.py` |
| B2 | Channel Adapter 抽象 | ⚠️ | `channel_ingress.py`；无 `channels/base.py` |
| B3 | `POST /channels/feishu/webhook` | ❌ | 501 stub · `api/channels.py` |
| B4 | `GET/PUT /api/channels/config` | ⚠️ | 改为 `PATCH /system/settings` channels 域 |
| B5 | 目录 `app/channels/feishu.py` | ❌ | 未建目录 |
| B6 | Phase 2 不做 Agent 编排 | 📋 | Phase 3 已实现 orchestrator |
| B7 | Phase 3 Orchestrator + Runners | ✅ | `orchestrator/` · `runners/` |
| B8 | 角色 Key Fernet 加密 | ✅ | `security/secrets.py` · `role_secrets` |
| B9 | 部署：本地 `./start.sh` 默认 | ✅ | 根目录 `start.sh` |
| B10 | Cloudflare Tunnel / systemd | ✅ | `deploy/` |
| B11 | 个人微信 Phase 2.x 后置 | ✅ | 走 ClawBot Bridge 设计，未做原生接入 |
| B12 | LangGraph 备选 | ➖ | 自研转移表，未引入 LangGraph |

---

## 3. IMPLEMENTATION.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| I1 | Phase 2a `GET /dashboard` | ✅ | `test_dashboard_contract.py` 35 keys |
| I2 | Phase 2b 项目/产出物读 API | ✅ | `projects.py` · `artifacts.py` |
| I3 | Phase 2c 写 API + refresh | ✅ | HITL/inbox/ceo/weekly 等 |
| I4 | Phase 2c 验收 全路径 HITL→ZIP→周报 | ✅ | IMPLEMENTATION 已 `[x]` |
| I5 | Phase 2c-opt `GET /events` SSE | ❌ | 无 `/events` |
| I6 | Phase 2c-opt patch 响应 | ❌ | 仍全量 refresh |
| I7 | Phase 2d 飞书 6 项任务 | ❌ | 见 CHANNELS §16 |
| I8 | Phase 2e 角色配置加密 | ✅ | `test_role_config_masks.py` |
| I9 | Phase 3a–f 编排骨架 | ✅ | `test_orchestrator.py` 等 |
| I10 | Phase 3 整体 Done（Brief→HITL-3 自动） | ⚠️ | Stub 可跑通；live LLM 非 CI 默认 |
| I11 | Phase 3e 会诊室 | ✅ | SQL `deliberation_*` · API · workroom 折叠 |
| I12 | Phase 4a 飞书 Ingress 深度 | ❌ | 未开始 |
| I13 | Phase 4b SSE 全覆盖 | ❌ | 仅 pulse/orchestration stream |
| I14 | `orchestrator_hooks` 写 API 挂钩 | ✅ | HITL/ceo 等 |

---

## 4. API.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| A1 | 前缀 `/api/v1` | ✅ | `main.py` prefix |
| A2 | Envelope `{ ok, data, error }` | ✅ | `deps.ok` / `fail` |
| A3 | Dashboard 顶层键与 mock 兼容 | ✅ | `GOLDEN_TOP_LEVEL_KEYS` == 35 |
| A4 | Workroom 产出物 `actions[]` | ✅ | `test_workroom_v2.py` |
| A5 | `PUT /roles/config/{id}` Key 打码 | ✅ | `apiKey.masked` |
| A6 | 飞书 webhook/send Phase 2d | ❌ | webhook 501；无 send |
| A7 | `GET /api/v1/events` SSE | ❌ | 文档 §7；未实现 |
| A8 | 写操作集成测试 | ✅ | 52 个 test_*.py |
| A9 | 金额单位「元」整数 | ✅ | mock 一致 |
| A10 | 头像 `POST /roles/{id}/avatar` | 📋 | **已实现**；API.md **未收录** |
| A11 | `/channels/*` | 📋 | **已实现** setup/inbound；API.md **未收录** |

---

## 5. AGENTS.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| G1 | 控制面 + 编排层分离 | ✅ | API vs `orchestrator/engine.py` |
| G2 | CEO 星型 + HITL，非群聊 | ✅ | dispatcher · 无 GroupChat |
| G3 | 转移表驱动工作流 | ✅ | `transitions.py` · `workflow_engine.py` |
| G4 | Phase 2 预留编排表 | ✅ | `agent_runs` · `deliberation_sessions` · `handoffs` SQL |
| G5 | Phase 3 CEO FAB 真实推理 | ⚠️ | `ceo_turn.py` ✅；无 Key 时 stub |
| G6 | 会诊室 API + Founder 插话 | ⚠️ | `POST .../founder-note` ✅；**无专用 UI** |
| G7 | 会诊上限（≤3 角色×≤2 轮） | ⚠️ | `deliberation.py` 有约束；需对照常量 |
| G8 | Handoff / Dispatch 事件 | ✅ | `engine.py` · `dispatch_feed` |
| G9 | Phase 3c Acme 全链验收 | ⚠️ | 测试有；依赖 stub/规则 |
| G10 | SSE `/events` 增量 | ❌ | 见 PULSE §15 |

---

## 6. AGENTS-COMPARE.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| C1 | 选型 D 变体（CEO 星型）+ C 的 HITL | ✅ | 架构一致 |
| C2 | 有限会诊室，非自由群聊 | ✅ | `orchestrator/deliberation.py` |
| C3 | 可审计 task/handoff 链 | ✅ | `tasks` · `dispatchFeed` · `agent_runs` |
| C4 | 对比表为决策参考 | 🔇 | 无「实现项」，设计已采纳 |

---

## 7. CEO-ORCHESTRATION-ROADMAP.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| CEO0 | Phase 0 稳基 | ✅ | 无循环 import · huawei 场景 |
| CEO1 | Phase 1 CEO Turn + commitments | ✅ | `ceo_turn.py` · `commitments.py` |
| CEO2 | Phase 1 验收 5 场景 | ⚠️ | 测试覆盖部分；live LLM 非必跑 |
| CEO3 | Phase 2 CEO Review **LLM + validator** | ⚠️ | **仅规则** `ceo_review.py` + validator |
| CEO4 | Phase 2 revision 最多 2 轮 + escalate | ✅ | `MAX_REVISION_ROUNDS=2` |
| CEO5 | Phase 3 multipart brief + md/pdf | ✅ | `ceo.py` · `ingress_documents.py` |
| CEO6 | Phase 3 验收 413 大文件 | ✅ | `test_ingress_documents.py` |
| CEO7 | Phase 4 Founder Profile + 建议采纳 | ✅ | `founder.py` · inbox UI |
| CEO8 | Phase 5 workflow_engine + next-steps | ✅ | `workflow_engine.py` · API |
| CEO9 | Phase 6 设置平台 Epic 1–5 | ⚠️ | 见 §8–9；Epic 4–5 部分 stub |
| CEO10 | 文档状态 v0.8.0 已实现 | ⚠️ | 核心 ✅；G5 LLM 内审、G2 skill 附件闭环弱 |
| CEO11 | G1–G8 产品目标 | ⚠️ | G3 渠道弱；G4 主动流程有 engine 缺演示 |

---

## 8. SETTINGS-PLATFORM-ROADMAP.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| S8-E0 | Epic 0 文档索引 | ⚠️ | 路线图 `[ ]` 更新 PRD/API **仍未做** |
| S8-E1 | Epic 1 设置 IA + 角色平台 | ⚠️ | 见 §10 SETTINGS-V2 细项 |
| S8-E1a | 验收：两块主视图无长 scroll | ✅ | system/roles segment |
| S8-E1b | 验收：新建 brand 可派活 | ✅ | `test_roles_registry.py` |
| S8-E1c | 验收：Pulse 不闪退 | ✅ | `isSettingsUiInteractive` |
| S8-E2 | Epic 2 Tool Registry + enforce | ✅ | `tools/registry.py` · `test_tools_registry.py` |
| S8-E2a | 验收：未授权 role 调用被拒 | ✅ | enforce in agent_loop |
| S8-E3 | Epic 3 Skill Hub + skill_proposal | ⚠️ | Hub ✅；**收件箱 UI 无 skill_proposal** |
| S8-E3a | 验收：Brief 附件 → skill 提案 | ❌ | 未接附件管线 |
| S8-E4 | Epic 4 MCP + 多模态 | ⚠️ | CRUD ✅；**stdio stub** · image 无实调 |
| S8-E5 | Epic 5 Skill 链 + 路由 | ⚠️ | executor ✅；**无链编辑器 UI** |
| S8-D1 | `meta.skillRoutes` 规则表 | ⚠️ | 后端 `presentation/skills.py` ✅；**UI 无** |

---

## 9. SETTINGS-IMPLEMENTATION.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| SI1 | Dashboard 域 6 个新增 | ✅ | conftest 35 keys 含全部 |
| SI2 | API 索引表 | ⚠️ | 缺 avatar · channels |
| SI3 | `settings.js` segment | ✅ | |
| SI4 | Skill 列表 + 导入 Modal | ✅ | |
| SI5 | MCP 添加 | ✅ | stub health |
| SI6 | enabledSkills 勾选 | ✅ | |
| SI7 | 后续：MCP stdio 真进程 | ❌ | 文档自述 stub |
| SI8 | 后续：image slot 实调 | ❌ | |
| SI9 | 后续：Skill drawer · 链 UI | ❌ | |
| SI10 | 测试 156 passed | 📋 | 当前 **160** |

---

## 10. SETTINGS-V2.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| SV1 | 系统/角色职责分离 | ✅ | segment 不交叉 |
| SV2 | Founder Profile editor | ✅ | |
| SV3 | 编排首屏 4 项开关 | ⚠️ | Pulse/Agency/Auto/CEO-LLM ✅；**缺 Proposal 日上限** |
| SV4 | 编排高级：pauseWhileCeoThread 等 | ⚠️ | 后端默认有；**设置 UI 未暴露** |
| SV5 | Skill Hub 搜索 + 详情 drawer | ⚠️ | 列表 ✅；**无搜索、无 drawer** |
| SV6 | MCP 每连接 pill + health Modal | ⚠️ | 列表行 ✅；health 为 stub |
| SV7 | 渠道 2 pill | ⚠️ | 已扩展 ClawBot 指引；**无凭证表单** |
| SV8 | 新增角色 Modal 字段 | ✅ | id/name/title/dept/caps/dispatchable |
| SV9 | 角色：身份/Profile/模型槽/Skill | ✅ | 含头像上传 v0.9.20 |
| SV10 | 模型槽 text/image/video/code | ⚠️ | UI 按 capabilities 显示 text/image/video |
| SV11 | API 表 §6 全部端点 | ⚠️ | 缺 avatar POST；其余 ✅ |
| SV12 | Tool 策略 chips | ❌ | `toolPolicy` 后端有，UI 无 |

---

## 11. SKILL-HUB.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| SK1 | 四层：Model/Skill/Tool/MCP | ✅ | 数据模型一致 |
| SK2 | 内置 Tool 清单 7+ | ✅ | `registry.py` 含 read/write/dispatch/propose 等 |
| SK3 | Skill import + activate | ✅ | `skills.py` |
| SK4 | enabledSkills 绑 role | ✅ | roleConfig |
| SK5 | skillRoutes 解析 | ✅ | `resolve_skill_for_task` |
| SK6 | CEO propose_skill_install | ✅ | `tools/handlers.py` |
| SK7 | inbox skill_proposal + install | ⚠️ | API ✅ · **前端 Modal 无** |
| SK8 | Hub UI：搜索/分类/drawer | ❌ | 仅列表前 20 |
| SK9 | Epic 4 mcp health 真探测 | ❌ | stub |
| SK10 | Epic 4 image slot run | ❌ | |

---

## 12. WORKROOM-V2.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| W1 | 文档状态「已实现」 | ✅ | |
| W2 | 焦点条 1 条 | ✅ | `workroom.js` |
| W3 | 阶段分组顺序 | ✅ | 评估→…→运营 |
| W4 | 状态符号 ⏳●↻○— | ✅ | `STATUS_DOT` |
| W5 | 会诊/结项/Brief 折叠 | ✅ | |
| W6 | 产出物 Viewer + 编辑 + diff | ✅ | artifact API + UI |
| W7 | HITL 条在工作室 | ✅ | |
| W8 | 不含 P&L（→ 经营） | ✅ | |
| W9 | `GET /projects/{id}/workroom` | ✅ | `test_workroom_v2.py` |
| W10 | 批量 HITL 在收件箱 | ✅ | IA 分离 |

---

## 13. FINANCE-V2.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| F1 | 经营 Tab 非 duplicate 周报/收件箱 | ✅ | IA |
| F2 | 四态 filter + 项目 P&L 卡 | ✅ | `finance.js` |
| F3 | 按角色成本表 | ✅ | |
| F4 | Token 近四周 | ✅ | |
| F5 | 导出 API | ✅ | `test_finance_export.py` |
| F6 | `PATCH /finance/period` | ✅ | |
| F7 | `PATCH /finance/projects/{id}` | ✅ | |
| F8 | 明细 drawer | ✅ | `financeDetailProjectId` |
| F9 | 币种 CNY · 简化损益 | ✅ | |

---

## 14. WEEKLY-V2.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| WK1 | blocks kind 上限 | ⚠️ | 渲染有；**生成端是否严格截断需看 presenter** |
| WK2 | highlights 默认折叠 | ✅ | `<details>` in `weekly.js` |
| WK3 | 历史 8 周 + 更早折叠 | ✅ | `WEEKLY_LIST_VISIBLE` |
| WK4 | 列表/详情 Modal | ✅ | |
| WK5 | send / export md | ✅ | `weekly/current/send` · exportMd |
| WK6 | export pdf | ✅ | `exportWeeklyPdf` |
| WK7 | API 路径表 | ✅ | `weekly.py` |
| WK8 | 不含待批 duplicate | ✅ | filter 设计 |

---

## 15. PULSE-AGENCY-SPEC.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| PA1 | Phase A checklist `[ ]` 8 项 | ⚠️ | 代码大多有；**文档未勾** |
| PA2 | Phase B Observe + proposal 去重 | ✅ | `test_agency.py` |
| PA3 | Phase C auto-dispatch | ✅ | `test_agency_phase_c.py` |
| PA4 | `/pulse/stream` 多模块 sig | ✅ | |
| PA5 | 验收1：关浏览器仍执行 | ✅ | pulse loop |
| PA6 | 验收2：重启无僵尸 running | ✅ | reconcile |
| PA7 | 验收3：handoff 60s 消费 | ⚠️ | 有 handoff 模块；阈值需运维验证 |
| PA8 | 验收4：SSE 后不全量 2s 轮询 | ❌ | 仍 15s `tickLiveSync` 全量 pull |
| PA9 | 验收5：Observe 不耗 LLM | ✅ | |
| PA10 | 验收6：CEO 对话时 pause Agency | ✅ | `pauseWhileCeoThreadPending` in agency |
| PA11 | runtimeSettings 设置页 | ⚠️ | 部分暴露；非全部 §14 字段 |
| PA12 | openCommitments 摘要 CEO UI | ✅ | `app.js` |

---

## 16. CHANNELS-INTEGRATION.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| CH1 | Phase Now：inbound + setup | ✅ | `channels.py` |
| CH2 | ClawBot CLI 指引 | ✅ | settings 渠道卡 |
| CH3 | Bridge URL 示例 | ✅ | setup API |
| CH4 | Phase 1 飞书 Webhook | ❌ | 501 |
| CH5 | Phase 1 飞书出站 | ❌ | |
| CH6 | Phase 1 凭证 UI | ❌ | |
| CH7 | `bridge/openclaw-opc/` | ❌ | 目录不存在 |
| CH8 | Phase 3 出站回复 | ❌ | |
| CH9 | systemSettings.channels 持久化 | ⚠️ | PATCH 支持；**无专用表单** |

---

## 17. PRODUCT-COMPLETION-ROADMAP.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| PC1 | 作为缺口汇总文档 | ✅ | 与本文一致 |
| PC2 | Phase 0 已完成项 | ✅ | avatar/settings/channels 设计 |
| PC3 | Phase 1–5 规划 | 🔇 | 规划本身，非实现 |

---

## 18. README.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| R1 | 快速启动 `./start.sh` | ✅ | |
| R2 | Phase 2a–c ✅ | ✅ | 含 2e · 见 DEV-STATUS |
| R3 | Phase 3a–f ✅ | ⚠️ | 骨架 ✅；LLM 依赖 Key |
| R4 | Phase 2d/4 飞书 ❌ | ✅ | 与代码一致 |
| R5 | LLM 表述 | ✅ | 「Stub 默认 / Key 可选 live」 |
| R6 | pytest 说明 | ✅ | |
| R7 | deploy 链接 | ✅ | |
| R8 | DEV-STATUS 链接 | ✅ | 2026-05-24 |

---

## 19. deploy/README.md

| ID | 设计条目 | 符合 | 证据 / 偏差 |
|----|----------|------|-------------|
| D1 | 本地 bind 127.0.0.1 | ✅ | |
| D2 | Cloudflare Tunnel 示例 | ✅ | `deploy/cloudflare/` |
| D3 | systemd unit | ✅ | |
| D4 | backup 脚本引用 | ✅ | `scripts/backup-data.sh` |
| D5 | `OPC_ACCESS_TOKEN` 应用层校验 | ❌ | 仅文档与 `.env.example` |
| D6 | DATA_DIR 持久化 | ✅ | |

---

## 20. reference/from-cluster/**（🔇 非实现契约）

| 说明 |
|------|
| 早期 Charter/SOP/示例交付物；**不参与**本仓库 API/看板验收。 |
| 角色 prompt 参考已迁入 `runners/prompts.py` / seed，非 1:1 文件对照。 |

---

## 21. 跨文档高频偏差（汇总）

| 主题 | 文档怎么说 | 代码现实 | 状态（2026-05-24） |
|------|------------|----------|-------------------|
| LLM | README/PRD「未做」 | Key 配置后可调；默认 Stub | ✅ 已同步 |
| 飞书 | 多文档 Phase 2d/4 必做 | Webhook 501 | ❌ backlog CH-1 |
| SSE | API.md `/events` | 仅 pulse stream | ✅ API 标 planned |
| CEO Review | LLM + validator | 仅 validator 规则 | ⚠️ 文档已标注 |
| Skill Hub UI | drawer/搜索/proposal | 列表 + API | ❌ backlog ST-2/3 |
| MCP/多模态 | Epic 4 Done | stub | ✅ Epic 标 ⚠️ |
| 渠道 connected | mock true | 非探测 | ❌ backlog CH-5 |
| 鉴权 | deploy Token | 未编码 | ❌ backlog UX-4 |
| API 文档 | 缺 avatar/channels | 已实现 | ✅ API.md 已增 |

---

## 22. 文档维护记录

**2026-05-24 已同步：** PRD §1.4 · IMPLEMENTATION 验收框 · README · API.md · SETTINGS Epic · PULSE · CEO Phase2 · CHANNELS · BACKEND · DEV-STATUS（SSOT）

**持续：** OpenAPI `/docs` 与 API.md 手工对齐；合并 PR 时更新 [DEV-STATUS.md](./DEV-STATUS.md) §2/§3。

---

## 23. 按优先级的「文档承诺 → 代码」补齐顺序

与 [PRODUCT-COMPLETION-ROADMAP.md](PRODUCT-COMPLETION-ROADMAP.md) · [DEV-STATUS.md §3](DEV-STATUS.md#3-未完成--部分完成开发-backlog) 一致：

1. ~~**文档同步**~~ ✅ 2026-05-24  
2. **飞书 + 渠道凭证 + Bridge** — 满足 BACKEND/PRD/CHANNELS  
3. **Skill proposal UI + SETTINGS-V2 缺口** — 满足 SKILL-HUB / Epic 3 验收  
4. **MCP/多模态真实执行或文档降级** — Epic 4 诚实状态  
5. **SSE/鉴权** — API.md + deploy 承诺  

---

*维护：任一 Epic/Phase 关闭时更新对应 § 行。Last updated: 2026-05-24.*
