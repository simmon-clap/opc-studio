#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { runClientPipeline, runOpcWeeklySubsidy } from "./pipeline.js";
import { listHitl, approveHitl } from "./hitl.js";
import { readRunsSince } from "./logger.js";
import { aggregateUsage } from "./tkn.js";
import { getRepoRoot } from "./roles.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = getRepoRoot();

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--" && argv[i + 1]) {
      args.cmd = argv[++i];
      continue;
    }
    if (argv[i] === "--project" && argv[i + 1]) {
      args.project = argv[++i];
      continue;
    }
    if (argv[i] === "--client" && argv[i + 1]) {
      args.client = argv[++i];
      continue;
    }
    if (argv[i] === "--brief" && argv[i + 1]) {
      args.brief = argv[++i];
      continue;
    }
    if (argv[i] === "approve" && argv[i + 1]) {
      args.approveId = argv[++i];
      continue;
    }
    args._.push(argv[i]);
  }
  return args;
}

function newProject({ client, brief }) {
  const slug = client.replace(/[^a-z0-9-]/gi, "-").toLowerCase();
  const root = path.join(REPO, "clients", slug);
  fs.mkdirSync(path.join(root, "handoffs"), { recursive: true });
  fs.mkdirSync(path.join(root, "deliverables"), { recursive: true });
  fs.mkdirSync(path.join(root, "hitl"), { recursive: true });
  fs.writeFileSync(
    path.join(root, "meta.json"),
    JSON.stringify(
      {
        project_id: slug,
        client_name: client,
        vertical: "invoice",
        status: "intake",
        token_budget: 150000,
        created_at: new Date().toISOString(),
      },
      null,
      2
    )
  );
  fs.writeFileSync(path.join(root, "brief.md"), brief || `# ${client}\n\n待补充需求。\n`);
  console.log(`Created project: ${root}`);
  return root;
}

function exportMetrics() {
  const runs = readRunsSince(30);
  const usage = aggregateUsage(30);
  const metrics = {
    generated_at: new Date().toISOString(),
    poc_cycles: [],
    token_cost: usage,
    hitl: { pending: 0, approved: 0 },
    pipeline_conversion: { leads: 0, poc: 0, won: 0 },
  };

  for (const d of fs.existsSync(path.join(REPO, "clients"))
    ? fs.readdirSync(path.join(REPO, "clients"))
    : []) {
    const metaPath = path.join(REPO, "clients", d, "meta.json");
    if (!fs.existsSync(metaPath)) continue;
    const m = JSON.parse(fs.readFileSync(metaPath, "utf8"));
    if (m.status === "pipeline_run" || m.status === "poc") metrics.pipeline_conversion.poc++;
    if (m.status === "won") metrics.pipeline_conversion.won++;
    if (m.created_at && m.last_run_at) {
      const days = (new Date(m.last_run_at) - new Date(m.created_at)) / 86400000;
      metrics.poc_cycles.push({ project_id: d, days: Math.round(days * 10) / 10 });
    }
  }

  const opcHitl = listHitl(path.join(REPO, "opc-community"), null);
  const clientHitl = [];
  for (const d of fs.existsSync(path.join(REPO, "clients"))
    ? fs.readdirSync(path.join(REPO, "clients"))
    : []) {
    clientHitl.push(...listHitl(path.join(REPO, "clients", d), null));
  }
  for (const h of [...opcHitl, ...clientHitl]) {
    if (h.status === "pending") metrics.hitl.pending++;
    else if (h.status === "approved") metrics.hitl.approved++;
  }

  const opcWeekly = path.join(REPO, "opc-community", "reports");
  if (fs.existsSync(opcWeekly)) {
    const reports = fs.readdirSync(opcWeekly).filter((f) => f.startsWith("weekly-"));
    metrics.pipeline_conversion.leads = reports.length > 0 ? 1 : 0;
  }

  metrics.hitl_edit_rate = metrics.hitl.approved
    ? Math.round((metrics.hitl.pending / (metrics.hitl.pending + metrics.hitl.approved)) * 100)
    : 0;

  const out = path.join(REPO, "dashboards", "metrics.json");
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify(metrics, null, 2));
  console.log(JSON.stringify(metrics, null, 2));
  return metrics;
}

async function main() {
  const cmd = process.argv[2];
  const args = parseArgs(process.argv);

  if (cmd === "new-project") {
    if (!args.client) {
      console.error("Usage: npm run new-project -- --client acme --brief \"...\"");
      process.exit(1);
    }
    newProject(args);
    return;
  }

  if (cmd === "pipeline") {
    const projectRoot = args.project
      ? path.resolve(args.project)
      : path.join(REPO, "clients", "demo-invoice");
    if (!fs.existsSync(projectRoot)) {
      console.error(`Project not found: ${projectRoot}`);
      process.exit(1);
    }
    const r = await runClientPipeline(projectRoot);
    console.log("Pipeline done:", r.results);
    console.log("Pending HITL:", r.hitl.filter((h) => h.status === "pending").map((h) => h.id));
    exportMetrics();
    return;
  }

  if (cmd === "workflow") {
    const name = args.cmd || args._[0];
    if (name === "opc-weekly-subsidy") {
      const r = await runOpcWeeklySubsidy();
      console.log("OPC weekly + subsidy done");
      console.log("Pending HITL:", r.hitl.filter((h) => h.status === "pending").map((h) => h.id));
      exportMetrics();
      return;
    }
    console.error("Unknown workflow:", name);
    process.exit(1);
  }

  if (cmd === "hitl") {
    const sub = process.argv[3] || "list";
    const projectRoot = args.project
      ? path.resolve(args.project)
      : path.join(REPO, "opc-community");
    if (sub === "list") {
      console.log(JSON.stringify(listHitl(projectRoot, "pending"), null, 2));
      return;
    }
    if (sub === "approve" && args.approveId) {
      approveHitl(projectRoot, args.approveId);
      console.log("Approved:", args.approveId);
      exportMetrics();
      return;
    }
    console.error("Usage: npm run hitl -- list | approve <id> [--project path]");
    process.exit(1);
  }

  if (cmd === "metrics") {
    exportMetrics();
    return;
  }

  console.log(`OPC Orchestration CLI

Commands:
  new-project   --client <slug> --brief "..."
  pipeline      --project <path>
  workflow      opc-weekly-subsidy
  hitl          list | approve <id> [--project path]
  metrics
`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
