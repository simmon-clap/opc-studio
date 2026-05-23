# 数据分级与隔离

## 目录隔离规则

```
opc-agent-cluster/
├── company/          # L1 内部
├── templates/        # L0 公开模板
├── clients/
│   ├── acme/         # L2 客户 acme 专属
│   └── beta-corp/    # L2 客户 beta 专属
└── orchestration/logs/  # L1 审计（含 project_id）
```

Agent Run 启动时必须携带 `project_id`；Orchestrator 校验路径前缀。

## 客户项目最小文件集

```
clients/{slug}/
├── brief.md              # Founder 输入的客户需求
├── meta.json             # 客户名、行业、预算、状态
├── handoffs/             # 角色间 JSON 交接物
├── deliverables/         # Agent 产出
└── hitl/                 # 待审批 / 已审批记录
```
