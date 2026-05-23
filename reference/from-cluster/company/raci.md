# RACI · 人类 Founder vs Agent 集群

**R** = Responsible（执行）　**A** = Accountable（最终负责）　**C** = Consulted　**I** = Informed

| 活动 | 你（Founder） | Product | Legal | Dev | Ops | CEO |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| 客户沟通与收需求 | **RA** | C | I | I | I | I |
| 需求理解与 PRD | A | **R** | C | C | I | I |
| 报价与合同 | **A** | C | **R** | I | I | C |
| 方案设计与 PoC | A | C | I | **R** | I | I |
| 集成与上线 | **A** | C | C | **R** | I | I |
| 项目排期与进度 | A | I | I | C | **R** | I |
| 客户沟通草稿 | **A** | C | C | I | **R** | I |
| 优先级与资源决策 | **A** | C | C | C | C | **R** |
| 对外承诺 / 定价 | **RA** | I | C | I | I | C |
| 补贴 / 退款 / 法律函 | **RA** | I | **R** | I | C | C |

## 你的工作流（典型）

1. **收需求**：和客户聊完，把纪要丢进 `clients/{name}/brief.md`。
2. **启动流水线**：`npm run pipeline -- --project ../clients/{name}`。
3. **审卡点**：PRD 确认 → 报价确认 → 交付物确认 → 对外发送。
4. **交付客户**：你亲自或经你审核后发出最终成果。

## Agent 不做的事

- 不代替你给客户打电话、发微信、发邮件（仅产出草稿）。
- 不代替你签合同、收款、开票。
- 不代替你做最终技术选型拍板（可给建议）。
