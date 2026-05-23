# Node.js 编排原型（v0.1 · 已归档）

这是 **opc-agent-cluster** 时期的本地 CLI 编排，**不是** OPC Studio 的运行时。

```bash
# 当年用法（仅供参考，需自行 npm install）
cd legacy-orchestration
npm run pipeline -- --project ../examples/demo-invoice
npm run hitl -- list
npm run metrics
```

Studio 等价能力：

| 原型 | Studio |
|------|--------|
| `workflows/*.yaml` | Python 工作流引擎 + `workflow_templates` |
| `hitl.js` | `hitl_queue` + 收件箱 API |
| `pipeline.js` | Orchestrator + Pulse `execution` 模块 |
| `tkn.js` | `token_runs` / `agent_runs` |

保留此目录只为对照设计，**不要**与 `backend/` 混用。
