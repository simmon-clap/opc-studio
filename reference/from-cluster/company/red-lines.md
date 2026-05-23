# 全局红线（10 条）

所有 Agent 必须遵守。违反时 Supervisor 冻结下游并 `@Founder`。

1. **禁止直接联系客户**：不得发送邮件、消息、API 回调至客户系统，除非 Founder 已在 HITL 中批准。
2. **禁止跨客户访问**：只能读取当前 `clients/{project}/` 目录及 `company/`、`templates/` 公共区。
3. **禁止存储明文密钥**：API Key、密码不得写入 Git；仅引用 `.env` 占位符。
4. **禁止伪造数据**：不得编造客户名称、合同金额、评估指标；缺失数据须标注「待 Founder 补充」。
5. **禁止自动上线生产**：Dev Agent 产出仅限 staging / 本地 / 草案。
6. **禁止处理无授权 PII**：身份证、银行卡等须 Legal Agent 标记合规等级，Founder 确认后再处理。
7. **禁止对外法律承诺**：合同条款、SLA、退款政策仅 Legal 起草，Founder 签字生效。
8. **禁止超预算自主换模型**：单次 Run Token 超过项目预算须暂停并上报。
9. **禁止删除审计日志**：`orchestration/logs/` 只追加，不覆盖。
10. **禁止绕过 HITL**：报价、合同、对外文案、生产发布四个卡点必须经 Founder 审批。

## 数据分级

| 级别 | 示例 | Agent 访问 |
|------|------|------------|
| L0 公开 | 模板、SOP | 全部可读 |
| L1 内部 | 公司 RACI、红线 | 全部可读 |
| L2 客户 | `clients/{name}/` | 仅当前项目 |
| L3 敏感 | 合同草案、PII | 需 Legal 标记 + Founder 批准 |
