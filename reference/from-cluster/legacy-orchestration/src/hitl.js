import fs from "fs";
import path from "path";
import crypto from "crypto";

export function hitlDir(projectRoot) {
  return path.join(projectRoot, "hitl");
}

export function createHitlRequest(projectRoot, { type, title, payloadPath, blocks = [] }) {
  const dir = hitlDir(projectRoot);
  fs.mkdirSync(dir, { recursive: true });
  const id = crypto.randomBytes(4).toString("hex");
  const req = {
    id,
    type,
    title,
    payload_path: payloadPath,
    blocks,
    status: "pending",
    created_at: new Date().toISOString(),
    approved_at: null,
    approved_by: null,
  };
  fs.writeFileSync(path.join(dir, `${id}.json`), JSON.stringify(req, null, 2));
  return req;
}

export function listHitl(projectRoot, status = "pending") {
  const dir = hitlDir(projectRoot);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")))
    .filter((r) => !status || r.status === status);
}

export function approveHitl(projectRoot, id, approvedBy = "founder") {
  const file = path.join(hitlDir(projectRoot), `${id}.json`);
  if (!fs.existsSync(file)) throw new Error(`HITL ${id} not found`);
  const req = JSON.parse(fs.readFileSync(file, "utf8"));
  req.status = "approved";
  req.approved_at = new Date().toISOString();
  req.approved_by = approvedBy;
  fs.writeFileSync(file, JSON.stringify(req, null, 2));
  if (req.type === "prd_scope") {
    const ptd = path.join(projectRoot, "handoffs/product-to-dev.json");
    if (fs.existsSync(ptd)) {
      const j = JSON.parse(fs.readFileSync(ptd, "utf8"));
      j.status = "approved";
      j.approved_by = approvedBy;
      j.approved_at = req.approved_at;
      fs.writeFileSync(ptd, JSON.stringify(j, null, 2));
    }
  }
  return req;
}
