# SOP · CEO：周报摘要 → Pipeline 决策

## 触发

运营周报完成 + metrics 更新后。

## 步骤

1. 读取 `opc-community/reports/weekly-*.md`（最新）。
2. 读取 `clients/*/meta.json` Pipeline 状态。
3. 读取 `orchestration/logs/` 本周 Token 汇总。
4. 输出 `company/decisions/weekly-{date}.md`。
5. 输出 `pipeline-decision.json`（Go/No-Go 列表）。

## HITL

战略合作、大额资源投入 — Founder。

## 完成定义

- 备忘录 ≤1 页
- 每条 Pipeline 有明确建议
