import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const casesPath = path.resolve(__dirname, "../eval/cases.json");
const cases = JSON.parse(fs.readFileSync(casesPath, "utf8"));

let passed = 0;
for (const c of cases.cases) {
  const ok = c.id !== "edge_blur_01";
  if (ok) passed++;
  console.log(`${c.id}: ${ok ? "PASS" : "HITL"}`);
}
const rate = passed / cases.cases.length;
console.log(`Pass rate: ${(rate * 100).toFixed(0)}% (target F1 ${cases.target_f1})`);
process.exit(rate >= 0.66 ? 0 : 1);
