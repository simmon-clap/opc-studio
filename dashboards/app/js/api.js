const API_BASE = "/api/v1";

async function apiFetch(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, opts);
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const json = await res.json();
    if (!res.ok || json.ok === false) {
      throw new Error(json.error?.message || `HTTP ${res.status}`);
    }
    return json;
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res;
}

async function apiGet(path) {
  return apiFetch("GET", path);
}

async function apiPost(path, body = {}) {
  return apiFetch("POST", path, body);
}

async function apiPatch(path, body) {
  return apiFetch("PATCH", path, body);
}

async function apiPut(path, body) {
  return apiFetch("PUT", path, body);
}

async function apiPostForm(path, formData) {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: formData });
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const json = await res.json();
    if (!res.ok || json.ok === false) {
      throw new Error(json.error?.message || `HTTP ${res.status}`);
    }
    return json;
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res;
}

async function postCeoBrief(text, files = []) {
  const trimmed = (text || "").trim();
  if (files?.length) {
    const fd = new FormData();
    fd.append("text", trimmed || "请阅读附件");
    files.forEach((f) => fd.append("files", f));
    return apiPostForm("/ceo/brief", fd);
  }
  return apiPost("/ceo/brief", { text: trimmed });
}

async function loadDashboard() {
  const json = await apiGet("/dashboard");
  return json.data;
}

async function refreshDashboard() {
  data = await loadDashboard();
  if (typeof Presentation !== "undefined") {
    Presentation.syncRoleLayout(data);
  }
  return data;
}

async function loadRoleConfigs() {
  const json = await apiGet("/roles/config");
  return json.data;
}

async function downloadBlobFromApi(path, filename) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      msg = json.error?.message || msg;
    } catch (_) {}
    throw new Error(msg);
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
