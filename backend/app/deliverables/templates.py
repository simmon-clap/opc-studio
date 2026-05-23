"""Structured deliverable templates and LLM prompt assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeliverableTemplate:
    template_id: str
    kind: str
    required_sections: tuple[str, ...]
    skeleton: str
    prompt_instructions: str
    max_tokens: int = 4000
    temperature: float = 0.35


TEMPLATES: dict[str, DeliverableTemplate] = {
    "legal.nda_mutual_zh": DeliverableTemplate(
        template_id="legal.nda_mutual_zh",
        kind="nda",
        required_sections=(
            "协议标题",
            "鉴于",
            "第一条",
            "保密信息",
            "保密义务",
            "例外",
            "期限",
            "返还",
            "违约",
            "适用法律",
            "签章",
        ),
        skeleton="""# 保密协议（双向）

**协议编号：** [待填写：NDA-编号]

**签署日期：** [待填写：签署日期]

**披露方（甲方）：** [待填写：甲方全称]
**接收方（乙方）：** [待填写：乙方全称]

（以下单称「一方」，合称「双方」）

## 鉴于

双方拟就 **[待填写：合作事项/项目名称]** 进行商业讨论与评估（「目的」），在讨论过程中可能互相披露保密信息。为保护双方合法权益，经友好协商，达成如下协议：

## 第一条 保密信息的定义

1.1 「保密信息」指一方（「披露方」）向另一方（「接收方」）以口头、书面、电子或其他形式披露的任何非公开信息，包括但不限于：
- 技术信息：源代码、算法、架构、API、数据模型、PoC 成果；
- 商业信息：报价、成本、客户名单、商业计划、合同条款；
- 数据与文档：PRD、设计稿、测试数据、运营数据；
- 任何标注「保密」或依性质应被合理视为保密的信息。

1.2 下列信息不属于保密信息：（a）接收方在披露前已合法持有且无保密义务；（b）非因接收方违约而进入公有领域；（c）接收方从第三方合法取得且无保密限制；（d）依法律法规或有权机关要求必须披露（接收方应事先通知披露方并协助寻求保护）。

## 第二条 保密义务

2.1 接收方仅可为实现「目的」使用保密信息，不得用于任何其他目的。
2.2 接收方应采取不低于保护自身同类保密信息的合理注意义务保护保密信息，仅限「需要知悉」的员工/顾问访问，并使其承担同等保密义务。
2.3 未经披露方书面同意，接收方不得向任何第三方披露保密信息。

## 第三条 期限与返还

3.1 本协议自签署之日起生效。保密义务自披露之日起 **[待填写：2]** 年内有效；合作终止后继续有效 **[待填写：1]** 年。
3.2 应披露方要求或合作终止时，接收方应在 **[待填写：15]** 个工作日内返还或销毁所有保密信息载体，并提供书面销毁证明（法律要求留存的除外）。

## 第四条 违约责任

4.1 违反本协议的一方应赔偿因此给守约方造成的直接经济损失。
4.2 若违约行为导致保密信息广泛泄露，守约方有权要求违约方承担 **[待填写：违约金金额或计算方式]** 的违约金（不影响继续履行保密义务及追究其他法律责任）。

## 第五条 适用法律与争议解决

5.1 本协议适用 **[待填写：中华人民共和国法律 / 其他]** 。
5.2 因本协议引起的争议，双方应先协商；协商不成的，提交 **[待填写：仲裁机构/法院及地点]** 解决。

## 第六条 其他

6.1 本协议构成双方就保密事项的完整约定。
6.2 本协议以中文书写，一式 **[待填写：2]** 份，双方各执一份，具有同等效力。

---

## 签章页

**甲方（披露方）：** [待填写：甲方全称]

授权代表：________________　　职务：________________

签署日期：________________

**乙方（接收方）：** [待填写：乙方全称]

授权代表：________________　　职务：________________

签署日期：________________
""",
        prompt_instructions="""你是一名面向 B2B 软件与 AI Agent 交付的资深法务顾问。请基于下方骨架输出**可直接用于商务谈判的完整双向保密协议（NDA）**。

硬性要求：
1. 保留全部章节结构与条款编号，不得省略「签章页」。
2. 根据项目背景填入可确定的商业表述；无法确定的统一用 `[待填写：说明]` 占位，并在文末附「Founder 待确认清单」（编号列出所有待填项）。
3. 用语正式、严谨，避免口语与空洞套话；禁止只写提纲或 bullet 摘要。
4. 针对 Agent/软件项目，保密信息定义须覆盖源代码、模型、Prompt、客户数据、PRD。
5. 输出纯正文 Markdown，不要 JSON，不要解释性前言。
""",
        max_tokens=6000,
        temperature=0.3,
    ),
    "product.prd_agent": DeliverableTemplate(
        template_id="product.prd_agent",
        kind="prd",
        required_sections=("目标", "范围", "用户", "验收", "HITL"),
        skeleton="""# PRD · [项目名称]

## 1. 背景与目标
## 2. 用户与场景
## 3. 范围（In / Out of Scope）
## 4. Agent 拓扑 / 功能模块
## 5. 非功能需求
## 6. 验收标准（可测试）
## 7. HITL 卡点
## 8. 里程碑与依赖
""",
        prompt_instructions="""你是资深产品经理，负责 Agent 交付类 PRD。输出完整 Markdown PRD，必须包含可测试的验收标准（checkbox 或表格）和 HITL 卡点说明。禁止空泛描述。""",
        max_tokens=5000,
    ),
    "legal.sow_fixed": DeliverableTemplate(
        template_id="legal.sow_fixed",
        kind="sow",
        required_sections=("工作范围", "交付物", "里程碑", "费用", "验收"),
        skeleton="""# 工作说明书（SOW）

## 1. 项目概述
## 2. 工作范围
## 3. 交付物清单
## 4. 里程碑与时间表
## 5. 费用与付款
## 6. 验收标准
## 7. 变更与假设
## 8. 签章
""",
        prompt_instructions="""输出专业 SOW Markdown，条款完整，费用与交付物表格化，未知项用 [待填写] 占位。""",
        max_tokens=5000,
    ),
    "legal.quote": DeliverableTemplate(
        template_id="legal.quote",
        kind="quote",
        required_sections=("报价", "范围", "付款"),
        skeleton="""# 项目报价单

| 项目 | 说明 | 金额（CNY） |
|------|------|-------------|
""",
        prompt_instructions="""输出报价单 Markdown 表格，含范围摘要、分期付款与有效期。""",
        max_tokens=3000,
    ),
    "ceo.memo": DeliverableTemplate(
        template_id="ceo.memo",
        kind="memo",
        required_sections=("结论", "风险", "建议"),
        skeleton="""# CEO 评估备忘

## 结论
## 关键风险
## 建议下一步
""",
        prompt_instructions="""简洁专业的 CEO 评估备忘，面向 Founder，3-5 段。""",
        max_tokens=2000,
    ),
    "dev.tech_spec": DeliverableTemplate(
        template_id="dev.tech_spec",
        kind="tech_spec",
        required_sections=("架构", "接口", "交付"),
        skeleton="""# 技术方案

## 架构
## 技术栈
## 接口与集成
## 部署与环境
## 自测计划
""",
        prompt_instructions="""输出可实施的技术方案 Markdown，含架构说明与自测清单。""",
        max_tokens=4000,
    ),
    "dev.demo": DeliverableTemplate(
        template_id="dev.demo",
        kind="demo",
        required_sections=("演示", "自测"),
        skeleton="""# Demo 交付说明

## 访问方式
## 功能范围
## 自测结果
""",
        prompt_instructions="""输出 Demo 说明，含 staging URL 占位 [待填写：URL] 与自测 checklist。""",
        max_tokens=2500,
    ),
    "dev.code_delivery": DeliverableTemplate(
        template_id="dev.code_delivery",
        kind="code",
        required_sections=("仓库", "运行", "测试"),
        skeleton="""# 代码交付说明

## 仓库 / 目录结构
## 环境与运行
## 测试与验证
""",
        prompt_instructions="""输出代码交付说明 Markdown，含目录结构（代码块）与运行步骤。""",
        max_tokens=3500,
    ),
    "ops.acceptance": DeliverableTemplate(
        template_id="ops.acceptance",
        kind="acceptance",
        required_sections=("验收", "清单"),
        skeleton="""# 验收报告

## 验收范围
## 验收清单
- [ ] 项 1
## 遗留问题
## 签字确认
""",
        prompt_instructions="""输出验收报告，checklist 可勾选，含签字确认区。""",
        max_tokens=3000,
    ),
    "ops.closure": DeliverableTemplate(
        template_id="ops.closure",
        kind="closure",
        required_sections=("结项", "清单"),
        skeleton="""# 结项清单

- [ ] 客户交付包
- [ ] 文档归档
- [ ] 收款确认
""",
        prompt_instructions="""输出结项 checklist Markdown。""",
        max_tokens=2000,
    ),
    "ops.email": DeliverableTemplate(
        template_id="ops.email",
        kind="email",
        required_sections=("Subject", "正文"),
        skeleton="""Subject: [待填写：邮件主题]

[正文]
""",
        prompt_instructions="""输出客户邮件草稿，第一行 Subject: 开头，正文专业简洁。""",
        max_tokens=1500,
    ),
    "ops.lead_record": DeliverableTemplate(
        template_id="ops.lead_record",
        kind="ops_record",
        required_sections=("客户", "阶段", "下一步"),
        skeleton="""# 线索台账

| 客户 | 阶段 | 下一步 | 负责人 | 备注 |
|------|------|--------|--------|------|
""",
        prompt_instructions="""输出线索台账 Markdown 表格。""",
        max_tokens=1500,
    ),
    "generic.markdown": DeliverableTemplate(
        template_id="generic.markdown",
        kind="doc",
        required_sections=(),
        skeleton="# 产出物\n\n",
        prompt_instructions="""输出完整 Markdown 产出物。""",
        max_tokens=3000,
    ),
}


def get_template(template_id: str) -> DeliverableTemplate:
    return TEMPLATES.get(template_id) or TEMPLATES["generic.markdown"]


def build_generation_prompt(
    spec: Any,
    *,
    project_id: str,
    client: str,
    task_title: str,
    context: str,
    project_stage: str = "",
) -> tuple[str, int, float]:
    """Return (user_prompt, max_tokens, temperature)."""
    tpl = get_template(spec.template_id)
    header = (
        f"**项目 ID：** {project_id}\n"
        f"**客户：** {client}\n"
        f"**阶段：** {project_stage or '未知'}\n"
        f"**任务：** {task_title}\n\n"
        f"**Founder / CEO 背景：**\n{context or '（无额外背景）'}\n\n"
    )
    body = (
        f"{tpl.prompt_instructions}\n\n"
        f"---\n\n"
        f"**文档骨架（须在此基础上补全为完整正文，不得仅复述标题）：**\n\n"
        f"{tpl.skeleton}\n"
    )
    return header + body, tpl.max_tokens, tpl.temperature
