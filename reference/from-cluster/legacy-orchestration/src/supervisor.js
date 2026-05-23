import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

function productDevApproved(projectRoot) {
  const ptd = path.join(projectRoot, "handoffs/product-to-dev.json");
  if (!fs.existsSync(ptd)) return false;
  try {
    return JSON.parse(fs.readFileSync(ptd, "utf8")).status === "approved";
  } catch {
    return false;
  }
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RULES_PATH = path.resolve(__dirname, "../../contracts/supervisor-rules.yaml");

export function loadRules() {
  if (!fs.existsSync(RULES_PATH)) return { routing: [], escalation_rules: [] };
  const raw = fs.readFileSync(RULES_PATH, "utf8");
  const routing = [];
  let current = null;
  for (const line of raw.split("\n")) {
    if (line.match(/^\s+-\s+trigger:/)) {
      current = { trigger: line.split("trigger:")[1].trim(), steps: [] };
      routing.push(current);
    } else if (current && line.includes("role:")) {
      current.steps.push({ role: line.split("role:")[1].trim() });
    }
  }
  return { routing, rulesPath: RULES_PATH };
}

export function routeForTrigger(trigger) {
  const { routing } = loadRules();
  return routing.find((r) => r.trigger === trigger) || null;
}

export function shouldBlock(step, projectRoot, hitlList) {
  const pending = new Set(hitlList.filter((h) => h.status === "pending").map((h) => h.type));
  if (step.role === "dev") {
    if (productDevApproved(projectRoot)) return null;
    if (pending.has("prd_scope")) return "blocked:prd_scope_hitl";
  }
  if (step.role === "legal" && pending.has("quote")) return "blocked:quote_hitl";
  return null;
}
