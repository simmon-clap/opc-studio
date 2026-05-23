# OPC 社区 · 狗食项目

本目录用于 **OPC 社区周报 + 补贴对账** 内部狗食流程。

## 数据

- `data/members.json` — 成员与等级
- `data/usage.json` — 用量排行
- `data/subsidy-pool.json` — 补贴池与差额

## 运行

```bash
cd ../orchestration
npm run opc-weekly
npm run hitl -- list --project ../opc-community
```

## 产出

- `reports/weekly-*.md`
- `reports/subsidy-reconciliation-*.md`
- `handoffs/ops-to-legal.json`
- `deliverables/subsidy-compliance-note.md`（Legal）
- `../company/decisions/weekly-*.md`（CEO）

差额 ≠ 0 时自动创建 `subsidy` 类型 HITL，需 Founder 审批后发放。
