import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");

function writeIfMissing(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  if (!fs.existsSync(file)) fs.writeFileSync(file, content);
  return file;
}

function mockTokens(role) {
  const base = { product: 4200, legal: 2800, dev: 8900, ops: 3100, ceo: 1500 };
  return { prompt: base[role] || 2000, completion: Math.floor((base[role] || 2000) * 0.3) };
}

export const roleRunners = {
  product(projectRoot, ctx) {
    const prd = path.join(projectRoot, "deliverables/prd.md");
    const acc = path.join(projectRoot, "deliverables/acceptance-criteria.md");
    const vertical = ctx.vertical || "invoice";
    writeIfMissing(
      prd,
      `# PRD · ${ctx.clientName || ctx.projectId}\n\n## 背景\n${ctx.brief || "见 brief.md"}\n\n## 垂直\n${vertical}\n\n## 流程\nOCR → 结构化 → 科目映射 → ERP 草稿（会计 HITL 复核）\n\n## 数据边界\n发票影像 L2；科目规则 L1；不含银行卡全号。\n`
    );
    writeIfMissing(
      acc,
      `# 验收标准\n\n- [ ] 增值税发票字段抽取 F1 ≥ 0.92\n- [ ] 科目推荐 Top3 命中率 ≥ 0.85\n- [ ] 单张处理 < 15s（P95）\n- [ ] 会计复核界面可编辑后过账\n- [ ] 审计日志可追溯\n`
    );
    const ptdPath = path.join(projectRoot, "handoffs/product-to-dev.json");
    const existing = fs.existsSync(ptdPath) ? JSON.parse(fs.readFileSync(ptdPath, "utf8")) : null;
    const handoff = {
      handoff_id: existing?.handoff_id || `ptd-${Date.now()}`,
      project_id: ctx.projectId,
      vertical,
      prd_path: "deliverables/prd.md",
      acceptance_path: "deliverables/acceptance-criteria.md",
      data_boundary: "invoice images L2; chart of accounts L1",
      poc_deadline_weeks: 3,
      status: existing?.status === "approved" ? "approved" : "pending_hitl",
      ...(existing?.status === "approved"
        ? { approved_by: existing.approved_by, approved_at: existing.approved_at }
        : {}),
    };
    fs.mkdirSync(path.join(projectRoot, "handoffs"), { recursive: true });
    fs.writeFileSync(ptdPath, JSON.stringify(handoff, null, 2));
    fs.writeFileSync(
      path.join(projectRoot, "handoffs/product-to-legal.json"),
      JSON.stringify(
        {
          handoff_id: `ptl-${Date.now()}`,
          project_id: ctx.projectId,
          contains_pii: false,
          data_classes: ["L2"],
          retention_days: 90,
          cross_border: false,
          status: "approved",
        },
        null,
        2
      )
    );
    return { outputs: [prd, acc], handoff, tokens: mockTokens("product") };
  },

  legal(projectRoot, ctx) {
    const quote = path.join(projectRoot, "deliverables/quote-draft.md");
    const contract = path.join(projectRoot, "deliverables/contract-summary.md");
    const dpa = path.join(projectRoot, "deliverables/dpa-checklist.md");
    writeIfMissing(
      quote,
      `# 报价草案\n\n| 阶段 | 金额（CNY） | 说明 |\n|------|------------|------|\n| 签约 | 30% | — |\n| PoC 验收 | 40% | 2–3 周 |\n| 集成上线 | 30% | — |\n\nToken 预算：8–15 万 tokens/月（估）\n`
    );
    writeIfMissing(contract, `# 合同要点\n\n- 数据仅用于发票记账场景\n- HITL 复核后入账\n- 引用 clause-library 标准条款\n`);
    writeIfMissing(
      dpa,
      `# DPA Checklist\n\n- [x] 目的限定\n- [x] 存储期限 90 天\n- [ ] 跨境（否）\n- [x] 第三方模型经 TKN L1\n`
    );
    const handoff = {
      handoff_id: `ltf-${Date.now()}`,
      project_id: ctx.projectId,
      quote_path: "deliverables/quote-draft.md",
      contract_path: "deliverables/contract-summary.md",
      dpa_path: "deliverables/dpa-checklist.md",
      hitl_types: ["quote", "contract"],
      status: "pending_hitl",
    };
    fs.writeFileSync(path.join(projectRoot, "handoffs/legal-to-founder.json"), JSON.stringify(handoff, null, 2));
    return { outputs: [quote, contract, dpa], handoff, tokens: mockTokens("legal") };
  },

  dev(projectRoot, ctx) {
    const pocDir = path.join(projectRoot, "deliverables/poc");
    fs.mkdirSync(pocDir, { recursive: true });
    const workflow = path.join(pocDir, "workflow.yaml");
    const envEx = path.join(pocDir, ".env.example");
    writeIfMissing(
      workflow,
      `name: invoice-accounting-poc\nnodes:\n  - id: ocr\n    tool: ocr_extract\n  - id: structure\n    model: tkn-l1\n  - id: map_account\n    tool: chart_lookup\n  - id: erp_draft\n    tool: erp_write_draft\n  - id: hitl_review\n    type: human_gate\n`
    );
    writeIfMissing(envEx, `TKN_BASE_URL=https://api.tkn.example/v1\nTKN_API_KEY=sk-...\n`);
    const integration = path.join(projectRoot, "deliverables/integration-checklist.md");
    const evalReport = path.join(projectRoot, "deliverables/eval-report.md");
    writeIfMissing(integration, `# 集成清单\n\n- [ ] ERP API 沙箱\n- [ ] OCR 服务\n- [ ] TKN L1 项目 Key\n`);
    writeIfMissing(evalReport, `# Eval Report\n\n| 用例 | 通过 |\n|------|------|\n| vat_invoice_01 | ✓ |\n| vat_invoice_02 | ✓ |\n| edge_blur_01 | ✗ → HITL |\n\n**F1 均值**: 0.93\n`);
    return { outputs: [workflow, integration, evalReport], tokens: mockTokens("dev") };
  },

  ops(_projectRoot, ctx, opcRoot) {
    const reportsDir = path.join(opcRoot, "reports");
    fs.mkdirSync(reportsDir, { recursive: true });
    const week = new Date().toISOString().slice(0, 10);
    const weekly = path.join(reportsDir, `weekly-${week}.md`);
    const recon = path.join(reportsDir, `subsidy-reconciliation-2026-05.md`);
    writeIfMissing(
      weekly,
      `# OPC 社区周报 · ${week}\n\n## 活跃\n- 活跃成员：128（+12% WoW）\n- 总消耗 tokens：2.4M\n\n## Top10 消耗\n| 成员 | tokens | 等级 |\n|------|--------|------|\n| dev_alice | 320k | Pro |\n| startup_bob | 210k | Standard |\n\n## L3 商机线索\n- startup_bob 咨询发票自动化\n\n## 下周\n- 补贴池补充 ¥50k\n`
    );
    writeIfMissing(
      recon,
      `# 补贴对账 · 2026-05\n\n| 项目 | 金额（分） |\n|------|------------|\n| 期初余额 | 5000000 |\n| 本期发放 | 1200000 |\n| 期末余额 | 3800000 |\n| 账面消耗应计 | 1210000 |\n| **差额** | **-10000** |\n\n> 差额需 Founder + Legal 复核\n`
    );
    const handoff = {
      handoff_id: `otl-${Date.now()}`,
      period: "2026-05",
      reconciliation_path: "opc-community/reports/subsidy-reconciliation-2026-05.md",
      variance_cents: -10000,
      subsidy_total_cents: 1200000,
      status: "pending_hitl",
    };
    fs.mkdirSync(path.join(opcRoot, "handoffs"), { recursive: true });
    fs.writeFileSync(path.join(opcRoot, "handoffs/ops-to-legal.json"), JSON.stringify(handoff, null, 2));
    return { outputs: [weekly, recon], handoff, tokens: mockTokens("ops") };
  },

  legal_opc(opcRoot) {
    const note = path.join(opcRoot, "deliverables/subsidy-compliance-note.md");
    writeIfMissing(note, `# 补贴合规复核\n\n- 对账差额 -10000 分：建议暂缓发放，核查 3 笔异常消耗\n- 条款：符合补贴池规则 §3.2\n`);
    return { outputs: [note], tokens: mockTokens("legal") };
  },

  ceo(companyRoot, ctx) {
    const decisions = path.join(companyRoot, "decisions");
    fs.mkdirSync(decisions, { recursive: true });
    const date = new Date().toISOString().slice(0, 10);
    const memo = path.join(decisions, `weekly-${date}.md`);
    writeIfMissing(
      memo,
      `# CEO 决策备忘 · ${date}\n\n## 建议\n1. **Go** startup_bob 发票 PoC（模板复用，2 周）\n2. **Defer** 补贴发放直至对账差额清零\n3. **Go** 社区 Pro 档位促销（ROI 正向）\n\n## 风险\n- Token 成本周环比 +18%\n`
    );
    const pipeline = path.join(decisions, "pipeline-decision.json");
    fs.writeFileSync(
      pipeline,
      JSON.stringify(
        {
          date,
          decisions: [
            { project_id: "startup-bob", decision: "go", priority: 2 },
            { project_id: "opc-subsidy", decision: "defer", priority: 1, reason: "reconciliation variance" },
          ],
        },
        null,
        2
      )
    );
    return { outputs: [memo, pipeline], tokens: mockTokens("ceo") };
  },
};

export function getRepoRoot() {
  return REPO_ROOT;
}
