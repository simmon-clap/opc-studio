# SOP · 运营：周报 + 补贴对账

## 触发

每周一或 `npm run workflow -- opc-weekly-subsidy`。

## 步骤

1. 拉取 `opc-community/data/members.json`、`usage.json`、`subsidy-pool.json`。
2. 生成 `reports/weekly-{YYYY-Www}.md`。
3. 生成 `reports/subsidy-reconciliation-{YYYY-MM}.md`。
4. 输出 `handoffs/ops-to-legal.json`。
5. 若差额 ≠ 0，创建 HITL `subsidy_reconciliation`。

## HITL

Founder 批准补贴发放；Legal 复核对账口径。

## 完成定义

- 周报含 Top10 消耗与 L3 商机线索
- 对账表期初 + 本期 = 期末（或标注待查项）
