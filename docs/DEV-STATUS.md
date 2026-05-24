# 开发状态 · 单一事实来源（SSOT）

> **代码基线：** `VERSION` 文件 · **v0.9.x** · **174 tests passed**（`cd backend && pytest -q`）  
> **最后同步：** 2026-05-23（全量完成 + 全测试）  
> **对照审计：** [DOC-COMPLIANCE-MATRIX.md](./DOC-COMPLIANCE-MATRIX.md) · **实施顺序：** [PRODUCT-COMPLETION-ROADMAP.md](./PRODUCT-COMPLETION-ROADMAP.md)

本文档汇总 **已完成 / 部分完成 / 未开始** 的开发任务；各规范文档的验收框应与此保持一致。

---

## 1. 阶段总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| Phase 1 Mock 看板 | ✅ Done | |
| Phase 2a 只读 Dashboard API | ✅ Done | 35 顶层键契约测试 |
| Phase 2b 项目/产出物/工作室 | ✅ Done | workroom v2 |
| Phase 2c 写 API + 状态机 | ✅ Done | HITL/inbox/ceo/weekly + **全写 API patch** |
| Phase 2d 飞书 Webhook | ✅ Done | 验签 · 出站 · 设置表单 |
| Phase 2e 角色配置加密 | ✅ Done | 分槽 Key · 头像上传 |
| Phase 3a 编排骨架 | ✅ Done | engine/transitions/dispatcher |
| Phase 3b–c CEO/角色 Runners | ✅ Done | Stub 默认；配置 Key 可走 LLM |
| Phase 3d–f 成本/多项目/会诊 | ✅ Done | agent_runs · 会诊 API · Founder 插话 UI |
| Phase 4 飞书深度 / 上云 | ✅ Done | 核心链路 + deploy 模板 |
| Pulse Phase A–C | ✅ Done | 运行时 + SSE patch 增量 |
| 设置 Epic 1–5 | ✅ Done | Tool/Skill/链/路由/MCP/编排 |
| 渠道微信 + 飞书 | ✅ Done | Bridge · Webhook · 设置 |

**LLM 说明：** `llm_client.py` + 角色 Key 配置后可用；**无 Key 时 Stub Runner**，前端有 Stub 横幅与 Key 向导。

**测试：** `./scripts/test-all.sh`（174 pytest + API smoke）

---

## 2. 已完成（按域 · 可关闭验收）

### 控制面 & 看板
- [x] Dashboard / health / 静态挂载 / 35 键契约
- [x] 项目/产出物/工作室/ ZIP 导出
- [x] **全部写 API 返回 DashboardPatch**（inbox/project/hitl/ceo/weekly/finance/founder/commitments/artifacts/channels）
- [x] `/events` + `/pulse/stream` patch 增量
- [x] `OPC_ACCESS_TOKEN` 中间件

### CEO 编排
- [x] Phase 0–5 + Review LLM + skillChainId 派活
- [x] PoC E2E 场景测试（`tests/scenarios/test_poc_e2e.py`）

### Pulse & Agency
- [x] coordinator · Agency Observe · auto-dispatch
- [x] CEO Deliberate LLM + **角色 Proposal Deliberate LLM**

### 设置 & 执行面
- [x] Epic 1–5 全 UI（Tool/Skill/链/路由/MCP stdio/编排高级）
- [x] MCP stdio 子进程 + image/video media_client
- [x] 经营 byCapability + 预算 inbox

### 渠道 & Agent
- [x] 微信 ClawBot + 飞书全链路
- [x] Stub 横幅 · Key 向导 · `scripts/demo-live-llm.sh`

---

## 3. 未完成 / 部分完成

| ID | 任务 | 状态 |
|----|------|------|
| OP-3 | Docker 单容器 | ➖ 不做 |
| DOC-10 | OpenAPI 与 API.md 持续对齐 | 🔄 持续 |

**Backlog 已全部关闭（除 OP-3 明确不做项）。**

---

## 4. 测试清单

| 命令 | 说明 |
|------|------|
| `cd backend && pytest -q` | 174 项单元/集成/场景 |
| `./scripts/test-all.sh` | pytest + 运行中 API smoke |
| `./scripts/demo-live-llm.sh` | Live LLM（需 Key） |

---

*更新规则：合并 PR 关闭开发任务时，同步修改本文并更新对应规范文档验收框。*
