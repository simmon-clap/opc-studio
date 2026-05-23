# 来自 `opc-agent-cluster` 的参考资产

| 项 | 内容 |
|----|------|
| 来源 | `~/Projects/opc-agent-cluster`（2026-05-21 Node.js 文件原型） |
| 状态 | **只读参考**，不参与 OPC Studio 运行时 |
| 主线代码 | 本仓库根目录 `backend/` · `dashboards/app/` |

---

## 为什么在这里

早期在 `opc-agent-cluster` 用 **文件夹 + Node CLI** 验证了 Agent 公司概念（Charter、SOP、Handoff、YAML 工作流）。  
产品化后全部迁到 **OPC Studio**（FastAPI + Web 看板）。此处保留原文档与样板，供角色 Prompt、红线、垂直场景参考。

**不要**在本目录改代码 expecting `./start.sh` 会读到这些文件。

---

## 目录索引

| 路径 | 用途 |
|------|------|
| [`company/`](company/) | RACI、10 条全局红线、数据分级 |
| [`roles/`](roles/) | 五角色 `charter.md` + `system-prompt.md`（比 `mock/dashboard.json` 一行 charter 更细） |
| [`sops/`](sops/) | 标准作业程序（周报、PRD、PoC、合同等） |
| [`contracts/`](contracts/) | Handoff JSON Schema、Supervisor 规则 |
| [`templates/`](templates/) | L3 垂直样板（发票 OCR / 财务记账） |
| [`examples/demo-invoice/`](examples/demo-invoice/) | 客户项目样板：brief、handoff、deliverables |
| [`examples/opc-community/`](examples/opc-community/) | 内部狗食：社区周报、补贴对账样板 |
| [`legacy-orchestration/`](legacy-orchestration/) | v0.1 Node 编排 CLI + YAML 工作流（历史） |
| [`legacy-dashboard/`](legacy-dashboard/) | 旧 KPI 页（读 `metrics.json`，非 Studio 看板） |

---

## 与 Studio 的对应关系

| cluster 概念 | framework 实现 |
|--------------|----------------|
| `roles/*/charter.md` | `mock/dashboard.json` → 设置页 → `role_config` |
| `orchestration/workflows/*.yaml` | `backend/app/orchestrator/workflow_engine.py` 转移表 |
| `contracts/handoff-schemas/` | `handoffs` 表 + Orchestrator 事件 |
| `company/red-lines.md` | 待迁入 Runner system prompt / 文档（可参考本文） |
| `npm run pipeline` | Pulse + Orchestrator + `./start.sh` |

---

## 后续可选

- 将 `roles/*/system-prompt.md` 合并进 Studio 设置页默认 Prompt
- 将 `company/red-lines.md` 写入 `docs/AGENTS.md` 或 Runner 约束
- cluster 根目录已放 `ARCHIVED.md`，避免再在旧路径开发
