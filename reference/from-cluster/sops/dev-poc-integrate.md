# SOP · 开发：Scaffold → Integrate → Eval

## 触发

`handoffs/product-to-dev.json` 状态为 `approved`。

## 步骤

1. **Scaffold**：从 `templates/{vertical}/poc/` 复制到 `deliverables/poc/`。
2. **Configure**：`.env.example` 填写 TKN L1 占位符。
3. **Integrate**：列出客户系统 API 于 `integration-checklist.md`。
4. **Eval**：运行 `templates/{vertical}/eval/` 用例，写 `eval-report.md`。
5. **Handoff**：`dev-to-ops.json` 含上线前检查项。

## HITL

生产发布、密钥注入 — Founder + Dev 双人确认。

## 完成定义

- 离线 eval 通过率 ≥ 目标（见模板 README）
- 无明文密钥入库
