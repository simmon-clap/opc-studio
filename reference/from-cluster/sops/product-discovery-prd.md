# SOP · 产品：Discovery → PRD → 验收标准

## 触发

Founder 写入 `clients/{slug}/brief.md` 并执行 `npm run pipeline`。

## 步骤

1. **Discovery**：从 brief 提取目标用户、KPI、约束、已有系统。
2. **模板匹配**：对照 `templates/` 选择垂直（invoice / exam / internal-flow）。
3. **PRD**：输出 `deliverables/prd.md`（≤2 页核心）。
4. **验收**：输出 `deliverables/acceptance-criteria.md`，每条可演示。
5. **Handoff**：生成 `product-to-dev.json`、`product-to-legal.json`。

## HITL

Founder 确认 PRD 范围与客户口头一致后，pipeline 继续 Dev/Legal。

## 完成定义

- PRD 含数据边界章节
- 验收项 ≥5 条且可测试
