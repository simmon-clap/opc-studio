# Handoff 契约

角色间交接使用 JSON，Schema 见 `handoff-schemas/`。

| 文件 | 从 → 到 | 说明 |
|------|---------|------|
| `product-to-dev.json` | 产品 → 开发 | PRD 路径、垂直、PoC 周期 |
| `product-to-legal.json` | 产品 → 法务 | PII、数据分级 |
| `ops-to-legal.json` | 运营 → 法务 | 补贴对账 |
| `legal-to-founder.json` | 法务 → Founder | 待 HITL 报价/合同 |

调度规则：[`supervisor-rules.yaml`](supervisor-rules.yaml)
