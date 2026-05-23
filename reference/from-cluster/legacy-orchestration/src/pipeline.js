import fs from "fs";
import path from "path";
import crypto from "crypto";
import { appendRunLog } from "./logger.js";
import { recordTokenUsage } from "./tkn.js";
import { createHitlRequest, listHitl } from "./hitl.js";
import { roleRunners, getRepoRoot } from "./roles.js";
import { routeForTrigger, shouldBlock } from "./supervisor.js";

function readJsonSafe(file) {
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function logRun({ runId, projectId, role, status, outputs, error }) {
  appendRunLog({ run_id: runId, project_id: projectId, role, status, outputs, error });
}

function runRole(role, fn, ctx) {
  const runId = crypto.randomBytes(8).toString("hex");
  try {
    const result = fn();
    const tokens = result.tokens || { prompt: 1000, completion: 300 };
    recordTokenUsage({
      projectId: ctx.projectId,
      role,
      promptTokens: tokens.prompt,
      completionTokens: tokens.completion,
      runId,
    });
    logRun({
      runId,
      projectId: ctx.projectId,
      role,
      status: "ok",
      outputs: (result.outputs || []).map((p) => path.relative(ctx.repoRoot, p)),
    });
    return result;
  } catch (e) {
    logRun({
      runId,
      projectId: ctx.projectId,
      role,
      status: "error",
      error: String(e.message),
    });
    throw e;
  }
}

export async function runClientPipeline(projectRoot) {
  const repoRoot = getRepoRoot();
  const meta = readJsonSafe(path.join(projectRoot, "meta.json")) || {};
  const briefPath = path.join(projectRoot, "brief.md");
  const brief = fs.existsSync(briefPath) ? fs.readFileSync(briefPath, "utf8") : "";
  const ctx = {
    repoRoot,
    projectId: meta.project_id || path.basename(projectRoot),
    clientName: meta.client_name,
    vertical: meta.vertical || "invoice",
    brief,
  };

  const route = routeForTrigger("new_client_project");
  const results = [];

  runRole("product", () => roleRunners.product(projectRoot, ctx), ctx);
  const ptd0 = readJsonSafe(path.join(projectRoot, "handoffs/product-to-dev.json"));
  if (ptd0?.status !== "approved") {
    createHitlRequest(projectRoot, {
      type: "prd_scope",
      title: "确认 PRD 范围",
      payloadPath: "deliverables/prd.md",
      blocks: ["dev"],
    });
  }

  runRole("legal", () => roleRunners.legal(projectRoot, ctx), ctx);
  createHitlRequest(projectRoot, {
    type: "quote",
    title: "确认报价草案",
    payloadPath: "deliverables/quote-draft.md",
    blocks: ["outbound_to_client"],
  });

  const hitl = listHitl(projectRoot);
  const block = shouldBlock({ role: "dev" }, projectRoot, hitl);
  if (block) {
    console.log(`[supervisor] Dev 等待 HITL: ${block} — 运行: npm run hitl -- approve <id> --project <path>`);
  } else {
    runRole("dev", () => roleRunners.dev(projectRoot, ctx), ctx);
    results.push("client-pipeline-complete");
  }

  meta.status = "pipeline_run";
  meta.last_run_at = new Date().toISOString();
  fs.writeFileSync(path.join(projectRoot, "meta.json"), JSON.stringify(meta, null, 2));
  return { ctx, route, results, hitl: listHitl(projectRoot) };
}

export async function runOpcWeeklySubsidy() {
  const repoRoot = getRepoRoot();
  const opcRoot = path.join(repoRoot, "opc-community");
  const ctx = { repoRoot, projectId: "opc-community" };

  runRole("ops", () => roleRunners.ops(null, ctx, opcRoot), ctx);
  const otl = readJsonSafe(path.join(opcRoot, "handoffs/ops-to-legal.json"));
  runRole("legal", () => roleRunners.legal_opc(opcRoot), ctx);

  if (otl && otl.variance_cents !== 0) {
    createHitlRequest(opcRoot, {
      type: "subsidy",
      title: "补贴对账差额复核",
      payloadPath: otl.reconciliation_path,
      blocks: ["subsidy_payout"],
    });
  }

  runRole("ceo", () => roleRunners.ceo(path.join(repoRoot, "company"), ctx), ctx);
  return { hitl: listHitl(opcRoot) };
}
