const ROLE_POS = {
  ceo: { x: 50, y: 22 },
  product: { x: 18, y: 52 },
  legal: { x: 82, y: 52 },
  dev: { x: 32, y: 82 },
  ops: { x: 68, y: 82 },
};

const ROLE_SHORT = { ceo: "CEO", product: "产品", legal: "法务", dev: "开发", ops: "运营" };

const STATUS_SVG = {
  working: '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="4"/></svg>',
  waiting: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  idle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>',
  blocked: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01"/><circle cx="12" cy="12" r="9"/></svg>',
};

const STAT_ICONS = {
  leads: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>',
  active: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  clarify: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01"/></svg>',
  hitl: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>',
  done: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>',
};

const ART_ICONS = {
  doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>',
  link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>',
  mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M22 6l-10 7L2 6"/></svg>',
};

const INBOX_CAT = {
  must_read: "必读",
  request: "请示",
  approval: "待批",
};

let data = null;
let inboxFilter = "all";
let inboxStatusFilter = "active";
let pnlFilter = "all";
let workroomProjectId = null;
let workroomArtifactId = null;

const CLIENT_STATUS = { active: "合作中", prospect: "洽谈", renewal: "续费", lead: "线索" };
const CLOSURE_STATUS = { awaiting_hitl: "待 HITL", in_closure: "结项中", closed: "已结项" };
const PNL_HEALTH = { healthy: "盈利", strong: "高毛利", watch: "需关注", pipeline: "线索", loss: "亏损" };
const PNL_FILTER = { all: "全部", healthy: "盈利", watch: "需关注", pipeline: "线索" };

async function init() {
  const res = await fetch("../../mock/dashboard.json");
  data = await res.json();
  document.getElementById("company-name").textContent = data.meta.company;
  updateBadges();
  renderOverview();
  renderProjects();
  renderClients();
  renderInbox();
  renderCosts();
  renderWeekly();
  bindNav();
  bindModal();
  bindSheet();
  document.getElementById("fab-ceo").onclick = openCeoOffice;
  document.getElementById("btn-settings").onclick = openSettings;
}

function updateBadges() {
  const unread = data.inbox.filter((i) => !i.read && (i.status || "active") === "active").length;
  document.getElementById("inbox-badge").textContent = unread;
  const weeklyBadge = document.getElementById("weekly-badge");
  if (weeklyBadge) {
    const draft = data.weeklyReport?.status === "draft";
    weeklyBadge.hidden = !draft;
    weeklyBadge.textContent = draft ? "1" : "0";
  }
}

function goToView(viewId) {
  document.querySelectorAll(".nav-item").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === viewId);
  });
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.getElementById(`view-${viewId}`)?.classList.add("active");
  if (viewId === "overview") requestAnimationFrame(() => drawLines(document.getElementById("collab-svg")));
}

function goToWeekly() {
  closeModal();
  closeSheet();
  goToView("weekly");
}

function bindNav() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => goToView(btn.dataset.view));
  });
}

function bindModal() {
  const backdrop = document.getElementById("modal-backdrop");
  document.getElementById("modal-close").onclick = closeModal;
  backdrop.addEventListener("click", (e) => { if (e.target === backdrop) closeModal(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeModal(); closeSheet(); } });
}

function bindSheet() {
  document.getElementById("sheet-close").onclick = closeSheet;
  document.getElementById("sheet-backdrop").addEventListener("click", (e) => {
    if (e.target.id === "sheet-backdrop") closeSheet();
  });
}

function openModal(html, className = "") {
  document.getElementById("modal-body").innerHTML = html;
  const panel = document.getElementById("modal-panel");
  panel.className = "modal glass " + className;
  document.getElementById("modal-backdrop").hidden = false;
  document.body.style.overflow = "hidden";
}

function closeModal() {
  document.getElementById("modal-backdrop").hidden = true;
  document.body.style.overflow = "";
}

function openSheet() {
  document.getElementById("sheet-backdrop").hidden = false;
  document.body.style.overflow = "hidden";
}

function closeSheet() {
  document.getElementById("sheet-backdrop").hidden = true;
  if (!document.getElementById("modal-backdrop").hidden) return;
  document.body.style.overflow = "";
}

function getProject(id) { return data.projects.find((p) => p.id === id); }
function getRole(id) { return data.roles.find((r) => r.id === id); }
function getClient(id) { return data.clients?.find((c) => c.id === id); }
function getArtifact(id) { return data.artifacts.find((a) => a.id === id); }
function getClosure(projectId) { return data.closure?.[projectId]; }
function getProjectPnL(projectId) { return data.costs?.byProject?.find((r) => r.projectId === projectId); }
function getProjectPnLRows() { return (data.costs?.byProject || []).filter((r) => r.projectId !== "_internal" && r.revenue != null); }
function getRoleTasks(roleId, status) { return data.tasks.filter((t) => t.roleId === roleId && t.status === status); }
function fmtMoney(n) { return `¥${(n || 0).toLocaleString()}`; }

function channelBadge(ch) {
  const c = data.channels[ch];
  if (!c) return `<span class="channel-badge channel-web">${ch}</span>`;
  return `<span class="channel-badge channel-${ch}">${c.label}</span>`;
}

function progressRing(pct, size = 44, sw = 3) {
  const r = (size - sw) / 2;
  const c = 2 * Math.PI * r;
  const off = c - (pct / 100) * c;
  return `<svg class="progress-ring" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle class="bg" cx="${size/2}" cy="${size/2}" r="${r}"/>
    <circle class="fg" cx="${size/2}" cy="${size/2}" r="${r}" stroke-dasharray="${c}" stroke-dashoffset="${off}"/>
  </svg>`;
}

function assigneeAvatars(ids, max = 4) {
  const html = ids.slice(0, max).map((id) => {
    const r = getRole(id);
    return r ? `<img src="../../assets/avatars/${id}.png" alt="${r.name}" title="${r.name}"/>` : "";
  }).join("");
  const more = ids.length > max ? `<span class="more">+${ids.length - max}</span>` : "";
  return `<div class="assignees">${html}${more}</div>`;
}

function simpleMarkdown(md) {
  return md
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^- \[ \] (.+)$/gm, "<li>☐ $1</li>")
    .replace(/^- \[x\] (.+)$/gm, "<li>☑ $1</li>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/^(?!<[hlu])((?!^$).+)$/gm, (m) => (m.startsWith("<") ? m : `<p>${m}</p>`));
}

function fmtRelative(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

/* ── Overview + Pulse ── */
function renderPulse() {
  const p = data.pulse;
  const alert = data.alerts?.[0];
  const el = document.getElementById("pulse-bar");
  if (!el || !p) return;
  el.innerHTML = `
    <div class="pulse-item"><span class="pulse-val">${p.activeProjects}</span><span class="pulse-lbl">进行中</span></div>
    <div class="pulse-divider"></div>
    <div class="pulse-item ${p.hitlPending ? "warn" : ""}"><span class="pulse-val">${p.hitlPending}</span><span class="pulse-lbl">待批</span></div>
    <div class="pulse-divider"></div>
    <div class="pulse-item"><span class="pulse-val">${p.leads}</span><span class="pulse-lbl">线索</span></div>
    <div class="pulse-divider"></div>
    <div class="pulse-item ${p.alerts ? "alert" : ""}"><span class="pulse-val">${p.alerts}</span><span class="pulse-lbl">告警</span></div>
    ${alert ? `<div class="pulse-banner">${alert.message}</div>` : ""}`;
}

function getCollaborations() {
  const pairs = new Set();
  data.projects.forEach((proj) => {
    const active = data.roles.filter(
      (r) => proj.assignees?.includes(r.id) && r.workStatus !== "idle" && r.projectIds.includes(proj.id)
    );
    for (let i = 0; i < active.length; i++) {
      for (let j = i + 1; j < active.length; j++) {
        pairs.add([active[i].id, active[j].id].sort().join(":"));
      }
    }
  });
  return [...pairs].map((k) => k.split(":"));
}

function renderOverview() {
  renderPulse();
  document.getElementById("role-nodes").innerHTML = data.roles.map((r) => {
    const pos = ROLE_POS[r.id];
    const tasks = r.runningCount + r.pendingCount;
    return `
      <div class="role-node" style="left:${pos.x}%;top:${pos.y}%" onclick="showRoleModal('${r.id}')" role="button">
        <div class="avatar-wrap">
          <div class="status-ring ${r.workStatus}"></div>
          <img src="../../assets/avatars/${r.id}.png" alt="${r.name}"/>
          <div class="status-icon ${r.workStatus}">${STATUS_SVG[r.workStatus]}</div>
        </div>
        <span class="name">${r.name}</span>
        <span class="role-label">${ROLE_SHORT[r.id]}</span>
        ${tasks > 0 ? `<span class="task-badge">${tasks}</span>` : ""}
      </div>`;
  }).join("");
  requestAnimationFrame(() => drawLines(document.getElementById("collab-svg")));
  window.onresize = () => drawLines(document.getElementById("collab-svg"));
}

function drawLines(svg) {
  const stage = document.getElementById("overview-stage");
  if (!stage || !svg) return;
  const rect = stage.getBoundingClientRect();
  svg.setAttribute("viewBox", `0 0 ${rect.width} ${rect.height}`);
  svg.innerHTML = "";
  getCollaborations().forEach(([a, b]) => {
    const pa = ROLE_POS[a], pb = ROLE_POS[b];
    if (!pa || !pb) return;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", (pa.x / 100) * rect.width);
    line.setAttribute("y1", (pa.y / 100) * rect.height);
    line.setAttribute("x2", (pb.x / 100) * rect.width);
    line.setAttribute("y2", (pb.y / 100) * rect.height);
    svg.appendChild(line);
  });
}

function showRoleModal(roleId) {
  const r = getRole(roleId);
  const running = getRoleTasks(roleId, "running");
  const pending = getRoleTasks(roleId, "pending");
  const extras = r.extras ? Object.entries(r.extras).map(([k, v]) => {
    const label = { decisionQueue: "决策队列", riskAlerts: "风险", reportStatus: "周报", prdProgress: "PRD", openQuestions: "待澄清", quotesPending: "待报价", complianceFlags: "合规", environment: "环境", selfTest: "自测", tokenUsageMock: "Token", pipelineChanges: "Pipeline", draftsPending: "草稿" }[k] || k;
    const val = Array.isArray(v) ? v.join(" · ") : v;
    return `<div class="config-row"><span class="k">${label}</span><span>${val}</span></div>`;
  }).join("") : "";

  const taskBlock = (tasks, title) => tasks.length ? `
    <div class="modal-section">
      <div class="modal-section-title">${title}</div>
      ${tasks.map((t) => {
        const proj = getProject(t.projectId);
        const acts = (t.activities || []).slice(-3).map((a) =>
          `<div class="activity-row"><span class="activity-time">${fmtRelative(a.at)}</span><span>${a.message}</span></div>`
        ).join("");
        return `
          <div class="task-card glass-inner">
            <div class="task-card-head">
              <div class="t">${t.title}</div>
              ${t.progress != null ? `<span class="task-pct">${t.progress}%</span>` : ""}
            </div>
            <div class="task-card-meta">${proj?.clientName || ""} · ${t.stage || ""}</div>
            ${t.progressNote ? `<div class="task-note">${t.progressNote}</div>` : ""}
            ${acts ? `<div class="activity-list">${acts}</div>` : ""}
          </div>`;
      }).join("")}
    </div>` : "";

  openModal(`
    <div class="modal-hero">
      <img src="../../assets/avatars/${r.id}.png" alt=""/>
      <div><h2>${r.name}</h2><div class="sub">${r.title}</div></div>
    </div>
    <div class="modal-stat-row">
      <div class="modal-stat"><div class="v">${r.load.current}/${r.load.max}</div><div class="l">负荷</div></div>
      <div class="modal-stat"><div class="v">${r.weeklyHours.actual}h</div><div class="l">本周</div></div>
      <div class="modal-stat"><div class="v">${STATUS_LABEL[r.workStatus] || r.workStatus}</div><div class="l">状态</div></div>
    </div>
    <div class="focus-line">${r.focus}</div>
    ${extras ? `<div class="config-grid" style="margin:0.75rem 0">${extras}</div>` : ""}
    ${taskBlock(running, "进行中")}
    ${taskBlock(pending, "排队中")}
  `, "wide");
}

const STATUS_LABEL = { idle: "空闲", working: "工作中", waiting: "等待", blocked: "阻塞" };

/* ── Projects ── */
function renderProjects() {
  document.getElementById("stats-row").innerHTML = Object.entries(data.stats).map(([key, s]) => `
    <button class="stat-chip glass" onclick="showStatsModal('${s.filter}')">
      <div class="val">${s.value}</div>
      <div class="lbl">${STAT_ICONS[key] || ""}<span>${s.label}</span></div>
    </button>`).join("");

  document.getElementById("projects-grid").innerHTML = data.projects.map((p) => {
    const artCount = data.artifacts.filter((a) => a.projectId === p.id).length;
    const closure = getClosure(p.id);
    const pnl = getProjectPnL(p.id);
    const pnlLine = pnl ? renderProjectPnLBadge(pnl) : "";
    return `
    <button class="project-card glass" onclick="openWorkroom('${p.id}')">
      <div class="project-top">
        <div class="project-name">${p.clientName.replace("（线索）", "")}</div>
        <span class="priority pri-${p.priority}">${p.priority}</span>
      </div>
      <div class="progress-ring-wrap">
        ${progressRing(p.progress || 0)}
        <div class="progress-meta"><div class="pct">${p.progress || 0}%</div><div class="stage">${(p.stage || "").replace(/阶段\d · /, "")}</div></div>
      </div>
      ${pnlLine}
      ${assigneeAvatars(p.assignees || [])}
      ${p.hitlPending ? `<div class="project-hitl">${p.hitlPending} 待批</div>` : ""}
      ${closure && closure.status !== "closed" ? `<div class="project-closure">${CLOSURE_STATUS[closure.status] || closure.status}</div>` : ""}
      ${artCount ? `<div class="project-card-hint"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/></svg>${artCount} 份产出 · 进入工作室</div>` : ""}
    </button>`;
  }).join("");
}

/* ── Clients ── */
function renderClients() {
  const root = document.getElementById("clients-root");
  if (!root || !data.clients) return;
  const totalRev = data.clients.reduce((s, c) => s + (c.totalRevenue || 0), 0);
  const totalRecv = data.clients.reduce((s, c) => s + (c.received || 0), 0);

  root.innerHTML = `
    <div class="clients-hero glass">
      <div><div class="sub">客户档案</div><div class="big">${data.clients.length}</div><div class="sub">家客户 / 线索</div></div>
      <div class="clients-hero-stats">
        <div><div class="v">${fmtMoney(totalRev)}</div><div class="l">合同额</div></div>
        <div><div class="v">${fmtMoney(totalRecv)}</div><div class="l">已收</div></div>
      </div>
    </div>
    <div class="clients-grid">
      ${data.clients.map((c) => {
        const projs = (c.projectIds || []).map((id) => getProject(id)).filter(Boolean);
        return `
        <button class="client-card glass" onclick="showClientDetail('${c.id}')">
          <div class="client-top">
            <div class="client-name">${c.name}</div>
            <span class="client-status st-${c.status}">${CLIENT_STATUS[c.status] || c.status}</span>
          </div>
          <div class="client-meta">${c.contact} · ${c.industry}</div>
          <div class="client-projects">${projs.map((p) => `<span class="proj-tag">${p.clientName.replace("（线索）", "")}</span>`).join("")}</div>
          <div class="client-revenue">
            <span>${fmtMoney(c.totalRevenue)}</span>
            <span class="recv">已收 ${fmtMoney(c.received)}</span>
          </div>
        </button>`;
      }).join("")}
    </div>`;
}

function showClientDetail(clientId) {
  const c = getClient(clientId);
  if (!c) return;
  const projs = (c.projectIds || []).map((id) => getProject(id)).filter(Boolean);
  const pays = (data.payments || []).filter((p) => p.clientId === clientId);
  const notes = (c.notes || []).map((n) =>
    `<div class="note-row"><span class="note-date">${n.at}</span><span>${n.text}</span></div>`
  ).join("") || '<p style="color:var(--text3);font-size:0.78rem">暂无纪要</p>';

  openModal(`
    <div class="modal-hero">
      <div class="client-avatar-lg">${c.name.slice(0, 1)}</div>
      <div><h2>${c.name}</h2><div class="sub">${c.contact} · ${c.industry}</div></div>
    </div>
    <div class="modal-stat-row">
      <div class="modal-stat"><div class="v">${fmtMoney(c.totalRevenue)}</div><div class="l">合同</div></div>
      <div class="modal-stat"><div class="v">${fmtMoney(c.received)}</div><div class="l">已收</div></div>
      <div class="modal-stat"><div class="v">${CLIENT_STATUS[c.status]}</div><div class="l">状态</div></div>
    </div>
    <div class="modal-section">
      <div class="modal-section-title">关联项目</div>
      ${projs.map((p) => `
        <div class="modal-list-item" onclick="closeModal();setTimeout(()=>openWorkroom('${p.id}'),250)">
          ${progressRing(p.progress || 0, 36, 2.5)}
          <div class="info"><h5>${p.clientName.replace("（线索）", "")}</h5><p>${p.progress || 0}% · ${(p.stage || "").replace(/阶段\d · /, "")}</p></div>
        </div>`).join("")}
    </div>
    <div class="modal-section">
      <div class="modal-section-title">收款</div>
      ${pays.length ? pays.map((p) => `
        <div class="config-row">
          <span class="k">${p.label}</span>
          <span>${fmtMoney(p.amount)} · ${p.status === "received" ? "✓ 已收" : "待收"}${p.at ? ` · ${p.at}` : ""}</span>
        </div>`).join("") : '<p style="color:var(--text3);font-size:0.78rem">暂无</p>'}
    </div>
    <div class="modal-section">
      <div class="modal-section-title">沟通纪要</div>
      <div class="notes-list">${notes}</div>
    </div>
  `, "wide");
}

function filterProjects(filter) {
  if (filter === "hitl") return data.projects.filter((p) => p.hitlPending);
  if (filter === "lead") return data.projects.filter((p) => p.pipelineColumn === "lead");
  return data.projects.filter((p) => p.pipelineColumn === filter);
}

function showStatsModal(filter) {
  const projects = filterProjects(filter);
  const label = Object.values(data.stats).find((s) => s.filter === filter)?.label || filter;
  openModal(`
    <h2 style="font-size:1.1rem;font-weight:700">${label}</h2>
    <p style="font-size:0.78rem;color:var(--text3);margin:0.5rem 0 1rem">${projects.length} 项</p>
    ${projects.map((p) => `
      <div class="modal-list-item" onclick="closeModal();setTimeout(()=>openWorkroom('${p.id}'),250)">
        ${progressRing(p.progress || 0, 36, 2.5)}
        <div class="info"><h5>${p.clientName}</h5><p>${p.progress || 0}%</p></div>
      </div>`).join("") || '<p style="color:var(--text3);text-align:center">暂无</p>'}
  `);
}

/* ── Workroom (A) ── */
function openWorkroom(projectId, artifactId) {
  workroomProjectId = projectId;
  const p = getProject(projectId);
  const arts = data.artifacts.filter((a) => a.projectId === projectId);
  workroomArtifactId = artifactId || (arts[0]?.id);

  document.getElementById("sheet-title").textContent = p.clientName.replace("（线索）", "");
  document.getElementById("sheet-progress").textContent = `${p.progress || 0}%`;

  document.getElementById("workroom-nav").innerHTML = arts.map((a) => {
    const role = getRole(a.roleId);
    return `
      <button class="art-item ${a.id === workroomArtifactId ? "active" : ""}" onclick="selectArtifact('${a.id}')">
        <span class="art-ico">${ART_ICONS[a.icon] || ART_ICONS.doc}</span>
        <span><div>${a.title}</div><div class="art-meta">${role?.name || ""} · ${fmtRelative(a.updatedAt)}</div></span>
      </button>`;
  }).join("") || '<p style="font-size:0.78rem;color:var(--text3);padding:0.5rem">暂无产出</p>';

  renderExportBar();
  renderWorkroomClosure();
  renderWorkroomFinance();
  renderWorkroomContent();
  openSheet();
}

function renderWorkroomClosure() {
  const panel = document.getElementById("closure-panel");
  const p = getProject(workroomProjectId);
  const cl = getClosure(workroomProjectId);
  if (!panel || !cl) { if (panel) panel.hidden = true; return; }

  const done = cl.checklist.filter((x) => x.done).length;
  const total = cl.checklist.length;
  panel.hidden = false;
  panel.innerHTML = `
    <div class="closure-head">
      <div>
        <div class="closure-title">结项清单</div>
        <div class="closure-sub">${CLOSURE_STATUS[cl.status] || cl.status} · ${done}/${total}</div>
      </div>
      ${cl.status === "in_closure" ? `<button class="btn-primary btn-sm" onclick="exportClientDeliveryZip()">导出客户 ZIP</button>` : ""}
      ${cl.status === "closed" ? `<span class="closure-closed">✓ ${cl.closedAt || "已结项"}</span>` : ""}
    </div>
    <div class="closure-list">
      ${cl.checklist.map((item) => {
        const role = getRole(item.roleId);
        return `
          <div class="closure-item ${item.done ? "done" : ""}">
            <span class="closure-check">${item.done ? "☑" : "☐"}</span>
            <span class="closure-label">${item.label}</span>
            <span class="closure-role">${role?.name || ""}</span>
          </div>`;
      }).join("")}
    </div>`;
}

function markClosureItem(projectId, itemId) {
  const cl = getClosure(projectId);
  const item = cl?.checklist?.find((x) => x.id === itemId);
  if (!item) return;
  item.done = true;
  renderWorkroomClosure();
}

function renderExportBar() {
  const p = getProject(workroomProjectId);
  const slug = (p?.clientName || "project").replace(/[^\w\u4e00-\u9fa5]+/g, "_").slice(0, 20);
  document.getElementById("export-bar").innerHTML = `
    <button class="export-btn" title="下载 MD" onclick="exportCurrentMd()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M12 18v-6M9 15l3 3 3-3"/></svg>
    </button>
    <button class="export-btn" title="下载 PDF" onclick="exportCurrentPdf()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M8 13h2v3M16 13h-2c0 2 2 2 2 2"/></svg>
    </button>
    <button class="export-btn" title="导出 ZIP 项目包" onclick="exportProjectZip()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
    </button>
    ${getClosure(workroomProjectId)?.status === "in_closure" ? `
    <button class="export-btn" title="客户交付 ZIP" onclick="exportClientDeliveryZip()" style="width:auto;padding:0 0.5rem;font-size:0.68rem;color:var(--accent)">客户包</button>` : ""}`;
}

function slugify(name) {
  return (name || "file").replace(/[（）\s]/g, "_").replace(/[^\w\u4e00-\u9fa5_-]/g, "").slice(0, 40);
}

function downloadBlob(content, filename, mime) {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mime });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function exportCurrentMd() {
  const art = getArtifact(workroomArtifactId);
  if (!art) return;
  const p = getProject(workroomProjectId);
  const name = `${slugify(p?.clientName)}_${slugify(art.title)}.md`;
  downloadBlob(art.content, name, "text/markdown;charset=utf-8");
}

function exportCurrentPdf() {
  const art = getArtifact(workroomArtifactId);
  if (!art || !window.jspdf) return;
  const p = getProject(workroomProjectId);
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const margin = 48;
  let y = margin;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.text(`${p?.clientName || ""} — ${art.title}`, margin, y);
  y += 28;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  const lines = doc.splitTextToSize(art.content.replace(/[#*`]/g, ""), 515);
  lines.forEach((line) => {
    if (y > 780) { doc.addPage(); y = margin; }
    doc.text(line, margin, y);
    y += 14;
  });
  doc.save(`${slugify(p?.clientName)}_${slugify(art.title)}.pdf`);
}

async function exportProjectZip() {
  if (!window.JSZip) return;
  const p = getProject(workroomProjectId);
  const arts = data.artifacts.filter((a) => a.projectId === workroomProjectId);
  if (!arts.length) return;
  const zip = new JSZip();
  const folder = zip.folder(slugify(p?.clientName) || "project");
  arts.forEach((a) => {
    folder.file(`${slugify(a.title)}.md`, a.content);
  });
  folder.file("README.txt", `OPC Studio 交付包\n项目：${p?.clientName}\n导出时间：${new Date().toLocaleString("zh-CN")}\n\n包含 ${arts.length} 份产出物（Markdown）`);
  const blob = await zip.generateAsync({ type: "blob" });
  downloadBlob(blob, `${slugify(p?.clientName)}_delivery.zip`, "application/zip");
}

async function exportClientDeliveryZip() {
  if (!window.JSZip) return;
  const p = getProject(workroomProjectId);
  const arts = data.artifacts.filter((a) => a.projectId === workroomProjectId);
  if (!arts.length) return;
  const zip = new JSZip();
  const folder = zip.folder(`${slugify(p?.clientName)}_客户交付`);
  arts.forEach((a) => {
    let content = a.content;
    if (a.demoUrl) content += `\n\n---\n演示链接：${a.demoUrl}`;
    folder.file(`${slugify(a.title)}.md`, content);
  });
  folder.file("交付说明.txt", `OPC Studio 客户交付包\n项目：${p?.clientName}\n交付日期：${new Date().toLocaleDateString("zh-CN")}\n\n本包为对外交付版本，不含内部备注。`);
  const blob = await zip.generateAsync({ type: "blob" });
  downloadBlob(blob, `${slugify(p?.clientName)}_客户交付.zip`, "application/zip");
  const cl = getClosure(workroomProjectId);
  if (cl) {
    const zipItem = cl.checklist.find((x) => x.label.includes("ZIP"));
    if (zipItem) zipItem.done = true;
    renderWorkroomClosure();
  }
}

function selectArtifact(id) {
  workroomArtifactId = id;
  document.querySelectorAll(".art-item").forEach((el) => el.classList.remove("active"));
  document.querySelector(`.art-item[onclick="selectArtifact('${id}')"]`)?.classList.add("active");
  renderWorkroomContent();
}

function renderWorkroomContent() {
  const art = getArtifact(workroomArtifactId);
  const el = document.getElementById("workroom-content");
  if (!art) { el.innerHTML = "<p style='color:var(--text3)'>选择左侧文档</p>"; return; }
  const versionTag = art.version ? `<span class="art-version">v${art.version}</span>` : "";
  const demoBtn = art.demoUrl ? `<a class="demo-link" href="${art.demoUrl}" target="_blank" rel="noopener">↗ 打开 Demo</a>` : "";
  el.innerHTML = `
    <div class="workroom-toolbar">
      <div class="workroom-meta">${versionTag}${demoBtn}</div>
      <div style="display:flex;gap:0.35rem">
        <button class="export-btn" style="width:auto;padding:0 0.65rem;font-size:0.72rem;gap:0.3rem" onclick="exportCurrentMd()">MD</button>
        <button class="export-btn" style="width:auto;padding:0 0.65rem;font-size:0.72rem" onclick="exportCurrentPdf()">PDF</button>
      </div>
    </div>
    <div class="md-content">${simpleMarkdown(art.content)}</div>`;
}

/* ── Inbox (C + approvals) ── */
function renderInbox() {
  const filters = [
    { id: "all", label: "全部" },
    { id: "must_read", label: "必读" },
    { id: "request", label: "请示" },
    { id: "approval", label: "待批" },
  ];
  const statusFilters = [
    { id: "active", label: "待办" },
    { id: "done", label: "已办" },
    { id: "archived", label: "归档" },
  ];

  document.getElementById("inbox-filters").innerHTML = `
    <div class="filter-row">${filters.map((f) => `
      <button class="filter-chip ${inboxFilter === f.id ? "active" : ""}" onclick="setInboxFilter('${f.id}')">${f.label}</button>
    `).join("")}</div>
    <div class="filter-row filter-row-sub">${statusFilters.map((f) => `
      <button class="filter-chip filter-chip-sm ${inboxStatusFilter === f.id ? "active" : ""}" onclick="setInboxStatusFilter('${f.id}')">${f.label}</button>
    `).join("")}</div>`;

  const items = data.inbox.filter((i) => {
    const status = i.status || "active";
    if (status !== inboxStatusFilter) return false;
    return inboxFilter === "all" || i.category === inboxFilter;
  });

  document.getElementById("inbox-list").innerHTML = items.length ? items.map((item) => `
    <button class="inbox-card glass ${item.read ? "" : "unread"}" onclick="openInboxItem('${item.id}')">
      <img class="inbox-avatar" src="../../assets/avatars/ceo.png" alt="CEO"/>
      <div class="inbox-body">
        <h4>${item.title}</h4>
        <p>${item.preview}</p>
        <div class="inbox-meta">
          <span class="cat-badge">${INBOX_CAT[item.category]}</span>
          ${channelBadge(item.channel)}
          <span class="cat-badge">${fmtRelative(item.at)}</span>
          ${item.resolution === "approved" ? '<span class="cat-badge resolved">已批准</span>' : ""}
          ${item.resolution === "rejected" ? '<span class="cat-badge rejected">已驳回</span>' : ""}
        </div>
      </div>
    </button>
  `).join("") : `<div class="empty-state glass" style="border-radius:14px;padding:2rem"><p>${inboxStatusFilter === "active" ? "收件箱为空" : "暂无记录"}</p></div>`;

  if (data.rejectHistory?.length && inboxStatusFilter === "active") {
    document.getElementById("inbox-list").innerHTML += `
      <div class="reject-history glass">
        <div class="modal-section-title">近期驳回</div>
        ${data.rejectHistory.map((r) => {
          const proj = getProject(r.projectId);
          return `<div class="reject-row"><span class="reject-type">${r.type}</span><span>${proj?.clientName || ""} · ${r.note}</span><span class="reject-at">${r.at}</span></div>`;
        }).join("")}
      </div>`;
  }
}

function setInboxFilter(id) {
  inboxFilter = id;
  renderInbox();
}

function setInboxStatusFilter(id) {
  inboxStatusFilter = id;
  renderInbox();
}

function openInboxItem(id) {
  const item = data.inbox.find((i) => i.id === id);
  if (!item) return;
  item.read = true;
  updateBadges();
  renderInbox();

  if (item.category === "approval" && item.hitlId) {
    openHitlDetail(item.hitlId);
    return;
  }

  if (item.weeklyReportId || item.title.includes("周报")) {
    openModal(`
      <div style="display:flex;gap:0.5rem;margin-bottom:0.75rem">${channelBadge(item.channel)}<span class="cat-badge">必读</span></div>
      <h2 style="font-size:1.05rem;font-weight:700">${item.title}</h2>
      <p style="font-size:0.82rem;color:var(--text2);margin:0.5rem 0 1rem;line-height:1.5">${item.preview}</p>
      <div class="weekly-preview glass-inner">${data.weeklyReport?.summary || ""}</div>
      <div class="btn-row" style="margin-top:1rem">
        <button class="btn-primary" onclick="goToWeekly()">阅读完整周报 →</button>
        <button class="btn-secondary" onclick="closeModal()">稍后</button>
      </div>
    `, "wide");
    return;
  }

  const art = item.artifactId ? getArtifact(item.artifactId) : null;
  let actions = "";
  if (item.category === "request") {
    actions = `
      <div class="btn-row" style="margin-top:1rem">
        <button class="btn-primary" onclick="resolveRequest('${item.id}','approve')">同意 PoC</button>
        <button class="btn-secondary" onclick="resolveRequest('${item.id}','discuss')">再议</button>
      </div>`;
  }

  openModal(`
    <div style="display:flex;gap:0.5rem;margin-bottom:0.75rem">${channelBadge(item.channel)}<span class="cat-badge">${INBOX_CAT[item.category]}</span></div>
    <h2 style="font-size:1.05rem;font-weight:700">${item.title}</h2>
    <p style="font-size:0.82rem;color:var(--text2);margin:0.5rem 0 1rem;line-height:1.5">${item.preview}</p>
    ${art ? `<div class="md-content" style="max-height:240px;overflow-y:auto;padding:0.75rem;background:rgba(0,0,0,0.03);border-radius:12px">${simpleMarkdown(art.content)}</div>` : ""}
    ${actions}
    <button class="btn-secondary" style="width:100%;margin-top:0.75rem" onclick="closeModal();openWorkroom('${item.projectId}'${item.artifactId ? `,'${item.artifactId}'` : ""})">进入项目工作室 →</button>
  `, "wide");
}

function openHitlDetail(hitlId) {
  const h = data.hitlQueue.find((x) => x.id === hitlId);
  if (!h) return;
  const art = data.artifacts.find((a) => a.projectId === h.projectId && a.type === "demo") || getArtifact(h.artifactId);

  openModal(`
    <h2 style="font-size:1.05rem;font-weight:700">${h.type} · ${h.title}</h2>
    <p style="font-size:0.82rem;color:var(--text2);margin:0.5rem 0">${h.summary}</p>
    ${art ? `<div class="md-content" style="max-height:200px;overflow-y:auto;padding:0.75rem;background:rgba(0,0,0,0.03);border-radius:12px;margin:0.75rem 0">${simpleMarkdown(art.content)}</div>` : ""}
    <input class="reject-input" placeholder="驳回意见（可选）" id="reject-note"/>
    <div class="btn-row" style="margin-top:0.75rem">
      <button class="btn-primary" onclick="approveHitl('${h.id}')">批准</button>
      <button class="btn-secondary" onclick="rejectHitl('${h.id}')">驳回</button>
    </div>
  `, "wide");
}

function resolveRequest(itemId, action) {
  const item = data.inbox.find((i) => i.id === itemId);
  if (!item) return;
  item.status = "done";
  item.resolution = action === "approve" ? "approved" : "discussed";
  item.resolvedAt = new Date().toISOString();
  closeModal();
  renderInbox();
}

function rejectHitl(id) {
  const item = data.hitlQueue.find((h) => h.id === id);
  const note = document.getElementById("reject-note")?.value?.trim() || "需修改后重新提交";
  if (!item || item.approved) return;
  data.rejectHistory.unshift({
    id: `rej-${Date.now()}`,
    hitlId: id,
    projectId: item.projectId,
    type: item.type,
    note,
    at: new Date().toISOString().slice(0, 16).replace("T", " "),
  });
  data.inbox.filter((i) => i.hitlId === id).forEach((i) => {
    i.status = "done";
    i.resolution = "rejected";
    i.read = true;
  });
  closeModal();
  renderInbox();
}

function approveHitl(id) {
  const item = data.hitlQueue.find((h) => h.id === id);
  if (!item || item.approved) return;
  item.approved = true;
  data.inbox.filter((i) => i.hitlId === id).forEach((i) => {
    i.read = true;
    i.status = "done";
    i.resolution = "approved";
    i.resolvedAt = new Date().toISOString();
  });
  data.pulse.hitlPending = Math.max(0, data.pulse.hitlPending - 1);
  if (data.stats.hitl) data.stats.hitl.value = Math.max(0, data.stats.hitl.value - 1);
  const acme = getProject("proj-acme");
  if (acme) {
    acme.hitlPending = null;
    acme.progress = 92;
    acme.stage = "阶段5 · 结项交付";
    acme.closureStatus = "in_closure";
  }
  const cl = getClosure(item.projectId);
  if (cl) {
    cl.status = "in_closure";
    const hitlItem = cl.checklist.find((x) => x.label.includes("HITL-3"));
    if (hitlItem) hitlItem.done = true;
    const opsItem = cl.checklist.find((x) => x.label.includes("验收"));
    if (opsItem) opsItem.done = true;
  }
  closeModal();
  updateBadges();
  renderInbox();
  renderProjects();
  renderOverview();
  renderClients();
  setTimeout(() => {
    openWorkroom(item.projectId);
    openModal(`
      <h2 style="font-size:1.05rem;font-weight:700">HITL-3 已批准 · 进入结项</h2>
      <p style="font-size:0.82rem;color:var(--text2);margin:0.75rem 0 1rem;line-height:1.5">运营将完成内部验收与客户交付 ZIP。可在工作室查看结项清单并导出客户包。</p>
      <div class="btn-row">
        <button class="btn-primary" onclick="closeModal()">继续结项</button>
        <button class="btn-secondary" onclick="closeModal();exportClientDeliveryZip()">导出客户 ZIP</button>
      </div>
    `);
  }, 300);
}

/* ── CEO Office + Mobile channels ── */
function openCeoOffice() {
  const ch = data.channels;
  const thread = data.ceoThread.map((m) => {
    const isFounder = m.direction === "founder_to_ceo";
    return `
      <div class="thread-msg ${isFounder ? "founder" : "ceo"}">
        <div class="bubble">${m.text}</div>
        <div class="bubble-meta">${channelBadge(m.channel)} · ${new Date(m.at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</div>
      </div>`;
  }).join("");

  openModal(`
    <div class="modal-hero" style="margin-bottom:0.75rem">
      <img src="../../assets/avatars/ceo.png" alt=""/>
      <div><h2>沈策 · CEO</h2><div class="sub">唯一管理接口</div></div>
    </div>
    <div class="channel-bar">
      <div class="channel-pill ${ch.feishu.connected ? "on" : ""}">${ch.feishu.label}<br><small>${ch.feishu.connected ? "已连接" : "—"}</small></div>
      <div class="channel-pill ${ch.wechat.connected ? "on" : ""}">${ch.wechat.label}<br><small>${ch.wechat.connected ? "已连接" : "—"}</small></div>
      <div class="channel-pill on">Web</div>
    </div>
    <p style="font-size:0.72rem;color:var(--text3);margin-bottom:0.75rem">移动端可在飞书 / 企微 @CEO 投递需求，与 Web 同步</p>
    <div class="thread">${thread}</div>
    <textarea class="brief-input" id="brief-input" placeholder="向 CEO 传达客户需求、纪要或指令…"></textarea>
    <div class="btn-row">
      <button class="btn-primary" onclick="submitBrief()">投递简报</button>
      ${data.weeklyReport?.status === "draft" ? `<button class="btn-secondary" onclick="goToWeekly()">W20 周报草稿</button>` : ""}
    </div>
  `, "ceo-office");
}

function submitBrief() {
  const text = document.getElementById("brief-input")?.value?.trim();
  if (!text) return;
  data.ceoThread.push({
    id: "thread-new",
    direction: "founder_to_ceo",
    channel: "web",
    text,
    at: new Date().toISOString(),
  });
  data.ceoThread.push({
    id: "thread-reply",
    direction: "ceo_to_founder",
    channel: "web",
    type: "ack",
    text: "已收到。正在评估并更新 Pipeline，稍后回复。",
    at: new Date().toISOString(),
  });
  closeModal();
  setTimeout(openCeoOffice, 200);
}

/* ── Finance (Costs + Revenue) ── */
function renderProjectPnLBadge(pnl) {
  if (!pnl?.health) return "";
  const h = pnl.health;
  if (h === "healthy" || h === "strong") {
    return `<div class="project-pnl pnl-${h}">毛利 ${fmtMoney(pnl.margin)} · ${pnl.marginPct}%</div>`;
  }
  if (h === "watch") {
    return `<div class="project-pnl pnl-watch">未签约 · 已耗 ${fmtMoney(pnl.cost)}</div>`;
  }
  if (h === "pipeline") {
    return `<div class="project-pnl pnl-pipeline">线索 · 成本 ${fmtMoney(pnl.cost || 0)}</div>`;
  }
  return `<div class="project-pnl pnl-loss">亏损 ${fmtMoney(Math.abs(pnl.margin))}</div>`;
}

function renderProjectPnLCard(row) {
  const p = getProject(row.projectId);
  const label = p?.clientName?.replace("（线索）", "") || row.label || row.projectId;
  const signed = row.revenue > 0;
  return `
    <button class="pnl-card glass pnl-${row.health}" onclick="showProjectPnL('${row.projectId}')">
      <div class="pnl-card-top">
        <div class="pnl-name">${label}</div>
        <span class="pnl-health">${PNL_HEALTH[row.health] || row.health}</span>
      </div>
      <div class="pnl-metrics">
        <div><span class="k">合同</span><span>${signed ? fmtMoney(row.revenue) : row.quoted ? `报价 ${fmtMoney(row.quoted)}` : "—"}</span></div>
        <div><span class="k">已收</span><span>${fmtMoney(row.received || 0)}</span></div>
        <div><span class="k">Token 成本</span><span>${fmtMoney(row.cost)}</span></div>
        <div><span class="k">毛利</span><span class="${row.margin >= 0 ? "pos" : "neg"}">${signed || row.margin < 0 ? fmtMoney(row.margin) : "—"}${row.marginPct ? ` (${row.marginPct}%)` : ""}</span></div>
      </div>
      ${row.note ? `<div class="pnl-note">${row.note}</div>` : ""}
    </button>`;
}

function setPnlFilter(id) {
  pnlFilter = id;
  renderCosts();
}

function showProjectPnL(projectId) {
  const row = getProjectPnL(projectId);
  const p = getProject(projectId);
  if (!row || !p) return;
  const signed = row.revenue > 0;
  const recvCover = row.cost > 0 && row.received ? (row.received / row.cost).toFixed(1) : null;

  openModal(`
    <h2 style="font-size:1.05rem;font-weight:700">${p.clientName.replace("（线索）", "")} · 项目盈亏</h2>
    <div class="modal-stat-row">
      <div class="modal-stat"><div class="v">${signed ? fmtMoney(row.revenue) : "—"}</div><div class="l">合同</div></div>
      <div class="modal-stat"><div class="v">${fmtMoney(row.received || 0)}</div><div class="l">已收</div></div>
      <div class="modal-stat"><div class="v">${fmtMoney(row.cost)}</div><div class="l">Token 成本</div></div>
      <div class="modal-stat"><div class="v" style="color:${row.margin >= 0 ? "var(--green)" : "var(--red)"}">${signed ? fmtMoney(row.margin) : fmtMoney(row.margin)}</div><div class="l">毛利</div></div>
    </div>
    <div class="config-grid" style="margin:0.75rem 0">
      <div class="config-row"><span class="k">健康度</span><span class="pnl-health-tag pnl-${row.health}">${PNL_HEALTH[row.health]}</span></div>
      ${row.quoted ? `<div class="config-row"><span class="k">报价区间</span><span>${fmtMoney(row.quoted)}</span></div>` : ""}
      ${row.pending ? `<div class="config-row"><span class="k">待收</span><span>${fmtMoney(row.pending)}</span></div>` : ""}
      ${recvCover ? `<div class="config-row"><span class="k">已收/成本</span><span>${recvCover}x 覆盖</span></div>` : ""}
      <div class="config-row"><span class="k">Token</span><span>${((row.tokens || 0) / 1000).toFixed(0)}k · ${row.sharePct}% 占比</span></div>
    </div>
    ${row.note ? `<div class="focus-line">${row.note}</div>` : ""}
    <div class="btn-row" style="margin-top:1rem">
      <button class="btn-primary" onclick="closeModal();openWorkroom('${projectId}')">进入工作室</button>
      ${signed ? `<button class="btn-secondary" onclick="closeModal();showClientDetail('${p.clientId}')">客户档案</button>` : ""}
    </div>
  `, "wide");
}

function renderProjectPnLSection() {
  const rows = getProjectPnLRows().filter((r) => {
    if (pnlFilter === "all") return true;
    if (pnlFilter === "healthy") return r.health === "healthy" || r.health === "strong";
    return r.health === pnlFilter;
  });
  const watchCount = getProjectPnLRows().filter((r) => r.health === "watch").length;

  return `
    ${watchCount ? `<div class="budget-alert glass pnl-watch-alert">${watchCount} 个项目需关注：未签约但已产生 Token 成本，建议设 PoC 上限或暂停投入</div>` : ""}
    <div class="filter-row" style="margin-bottom:0.65rem">
      ${Object.entries(PNL_FILTER).map(([id, label]) => `
        <button class="filter-chip filter-chip-sm ${pnlFilter === id ? "active" : ""}" onclick="setPnlFilter('${id}')">${label}</button>
      `).join("")}
    </div>
    <div class="pnl-grid">${rows.map(renderProjectPnLCard).join("") || '<p class="empty-inline">暂无</p>'}</div>`;
}

function renderWorkroomFinance() {
  const row = getProjectPnL(workroomProjectId);
  const el = document.getElementById("workroom-finance");
  if (!el) return;
  if (!row?.health) { el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = `
    <div class="workroom-finance-inner glass-inner">
      <div class="wf-label">项目盈亏</div>
      <div class="wf-metrics">
        ${row.revenue > 0 ? `<span>合同 ${fmtMoney(row.revenue)}</span>` : row.quoted ? `<span>报价 ${fmtMoney(row.quoted)}</span>` : ""}
        <span>成本 ${fmtMoney(row.cost)}</span>
        ${row.revenue > 0 ? `<span class="${row.margin >= 0 ? "pos" : "neg"}">毛利 ${fmtMoney(row.margin)}</span>` : `<span class="pnl-watch">已耗 ${fmtMoney(row.cost)}</span>`}
      </div>
      <button class="wf-link" onclick="showProjectPnL('${workroomProjectId}')">详情</button>
    </div>`;
}

function renderCosts() {
  const c = data.costs;
  if (!c) return;
  const s = c.summary;
  const budgetPct = Math.round((s.totalCost / s.monthlyBudget) * 100);
  const maxWeek = Math.max(...c.weekly.map((w) => w.cost));
  const marginColor = (s.marginPct || 0) >= 80 ? "var(--green)" : "var(--orange)";

  document.getElementById("costs-root").innerHTML = `
    ${s.budgetAlert ? `<div class="budget-alert glass">${s.budgetAlertMessage || "Token 预算告警"}</div>` : ""}
    <div class="finance-grid">
      <div class="finance-card glass">
        <div class="sub">本月收入（合同）</div>
        <div class="big">${fmtMoney(s.revenue)}</div>
        <div class="sub">已收 ${fmtMoney(s.received)} · 待收 ${fmtMoney(s.pending)}</div>
      </div>
      <div class="finance-card glass">
        <div class="sub">Token 成本</div>
        <div class="big">${fmtMoney(s.totalCost)}</div>
        <div class="sub">${(s.totalTokens / 1000).toFixed(0)}k tokens</div>
      </div>
      <div class="finance-card glass highlight">
        <div class="sub">毛利</div>
        <div class="big" style="color:${marginColor}">${fmtMoney(s.margin)}</div>
        <div class="sub">毛利率 ${s.marginPct}%</div>
      </div>
    </div>
    <div class="cost-hero glass">
      <div>
        <div class="sub">${c.period} · Token 预算</div>
        <div class="big">${fmtMoney(s.totalCost)}</div>
        <div class="sub">预算 ${fmtMoney(s.monthlyBudget)} · 剩余 ${fmtMoney(s.budgetRemaining)}</div>
      </div>
      <div class="budget-ring">
        ${progressRing(budgetPct, 72, 4)}
        <span>${budgetPct}%</span>
      </div>
    </div>
    <div class="cost-section">
      <h3>按角色</h3>
      <div class="role-cost-list">
        ${c.byRole.map((row) => {
          const r = getRole(row.roleId);
          const cfg = data.roleConfig?.find((x) => x.roleId === row.roleId);
          return `
          <button class="role-cost-row glass" onclick="showRoleConfig('${row.roleId}')">
            <img src="../../assets/avatars/${row.roleId}.png" alt=""/>
            <div class="info">
              <div class="name">${r?.name} · ${ROLE_SHORT[row.roleId]}</div>
              <div class="bar-wrap"><div class="bar" style="width:${row.sharePct}%"></div></div>
            </div>
            <div class="amt">
              <div class="c">¥${row.cost}</div>
              <div class="t">${(row.tokens / 1000).toFixed(0)}k · ${cfg?.model || row.model}</div>
            </div>
          </button>`;
        }).join("")}
      </div>
    </div>
    <div class="cost-section">
      <h3>项目盈亏 · 确保每个项目赚钱</h3>
      ${renderProjectPnLSection()}
    </div>
    <div class="cost-section">
      <h3>Token 成本分布</h3>
      <div class="proj-cost-grid">
        ${c.byProject.filter((r) => r.projectId !== "_internal").map((row) => {
          const p = getProject(row.projectId);
          const label = p?.clientName?.replace("（线索）", "") || row.label || row.projectId;
          return `<button class="proj-cost-chip glass" onclick="showProjectPnL('${row.projectId}')"><div class="v">${fmtMoney(row.cost)}</div><div class="l">${label}<br>${row.sharePct}%</div></button>`;
        }).join("")}
        ${(() => {
          const internal = c.byProject.find((r) => r.projectId === "_internal");
          return internal ? `<div class="proj-cost-chip glass"><div class="v">${fmtMoney(internal.cost)}</div><div class="l">${internal.label}<br>${internal.sharePct}%</div></div>` : "";
        })()}
      </div>
    </div>
    <div class="cost-section">
      <h3>近四周</h3>
      <div class="week-bars glass" style="padding:1rem;border-radius:14px">
        ${c.weekly.map((w) => `
          <div class="week-bar">
            <div class="bar" style="height:${Math.max(12, (w.cost / maxWeek) * 64)}px"></div>
            <span class="lbl">${w.week}</span>
          </div>`).join("")}
      </div>
    </div>`;
}

function showRoleConfig(roleId) {
  const r = getRole(roleId);
  const cfg = data.roleConfig?.find((x) => x.roleId === roleId);
  const cost = data.costs?.byRole?.find((x) => x.roleId === roleId);
  if (!cfg) return;
  openModal(`
    <div class="modal-hero">
      <img src="../../assets/avatars/${roleId}.png" alt=""/>
      <div><h2>${r?.name}</h2><div class="sub">${r?.title}</div></div>
    </div>
    <div class="config-grid">
      <div class="config-row"><span class="k">模型</span><span>${cfg.model}</span></div>
      <div class="config-row"><span class="k">API</span><span>${cfg.apiProvider}</span></div>
      <div class="config-row"><span class="k">月预算</span><span>¥${cfg.monthlyBudget}</span></div>
      <div class="config-row"><span class="k">本月已用</span><span>¥${cost?.cost || 0}</span></div>
      <div class="config-row"><span class="k">工具</span><span>${cfg.tools.join(" · ")}</span></div>
    </div>
    <p style="font-size:0.72rem;color:var(--text3);margin-top:1rem">Phase 2：在此配置 API Key 与模型路由</p>
  `, "wide");
}

/* ── Weekly Report ── */
function renderWeekly() {
  const root = document.getElementById("weekly-root");
  const wr = data.weeklyReport;
  if (!root || !wr) return;
  const author = getRole(wr.author);
  const perf = data.rolePerformance || [];
  const fs = wr.financeSnapshot;
  const urgencyLabel = { today: "今日", this_week: "本周", later: "可缓" };

  const pipelineRows = (wr.pipelineSnapshot || []).map((row) => {
    const p = getProject(row.projectId);
    return `
      <div class="pipeline-row ${row.progress >= 100 ? "done" : ""}">
        <div class="pipeline-name">${row.label || p?.clientName?.replace("（线索）", "")}</div>
        <div class="pipeline-bar-wrap"><div class="pipeline-bar" style="width:${row.progress || 0}%"></div></div>
        <div class="pipeline-meta">${row.progress || 0}% · ${row.stage}${row.note ? ` · ${row.note}` : ""}</div>
      </div>`;
  }).join("");

  const decisions = (wr.pendingDecisions || []).map((d) => `
    <button class="decision-chip glass" onclick="openWorkroom('${d.projectId}')">
      <span class="dec-urgency u-${d.urgency}">${urgencyLabel[d.urgency] || d.urgency}</span>
      <span>${d.title}</span>
    </button>`).join("");

  root.innerHTML = `
    <div class="weekly-hero glass">
      <div class="weekly-hero-left">
        <img src="../../assets/avatars/ceo.png" alt="CEO" class="weekly-ceo-avatar"/>
        <div>
          <div class="sub">CEO 一页纸周报 · ${wr.week}</div>
          <div class="weekly-period">${wr.period}</div>
          <div class="weekly-status st-${wr.status}">${wr.status === "draft" ? "草稿待发送" : wr.status === "sent" ? "已发送" : wr.status}</div>
        </div>
      </div>
      <div class="weekly-actions">
        <button class="btn-secondary btn-sm" onclick="exportWeeklyMd()">导出 MD</button>
        <button class="btn-secondary btn-sm" onclick="exportWeeklyPdf()">PDF</button>
        <button class="btn-primary btn-sm" onclick="sendWeeklyMock()" ${wr.status === "sent" ? "disabled" : ""}>${wr.status === "draft" ? "发送给 Founder" : "已发送"}</button>
      </div>
    </div>

    <div class="weekly-one-pager">
      <div class="weekly-panel glass">
        <h3>Pipeline 快照</h3>
        <div class="pipeline-list">${pipelineRows}</div>
      </div>
      <div class="weekly-panel glass">
        <h3>待你拍板</h3>
        <div class="decision-list">${decisions || '<p class="empty-inline">暂无</p>'}</div>
        ${fs ? `
        <h3 style="margin-top:1rem">经营快照</h3>
        <div class="finance-mini">
          <div><span class="k">合同</span><span>${fmtMoney(fs.revenue)}</span></div>
          <div><span class="k">已收</span><span>${fmtMoney(fs.received)}</span></div>
          <div><span class="k">Token 成本</span><span>${fmtMoney(fs.cost)}</span></div>
          <div><span class="k">毛利</span><span class="margin">${fmtMoney(fs.margin)} (${fs.marginPct}%)</span></div>
        </div>` : ""}
      </div>
    </div>

    <div class="weekly-summary glass"><strong>Executive Summary</strong><br>${wr.summary}</div>
    ${wr.sections.map((sec) => `
      <div class="weekly-section glass">
        <h3>${sec.title}</h3>
        <div class="md-content">${simpleMarkdown(sec.content)}</div>
      </div>`).join("")}
    <div class="cost-section">
      <h3>五部门贡献（摘要，非五份长文）</h3>
      <div class="role-perf-grid">
        ${perf.map((p) => {
          const r = getRole(p.roleId);
          const hl = wr.roleHighlights?.find((h) => h.roleId === p.roleId);
          return `
          <div class="role-perf-card glass">
            <img src="../../assets/avatars/${p.roleId}.png" alt=""/>
            <div class="perf-info">
              <div class="name">${r?.name}</div>
              <div class="perf-stats">${p.tasksCompleted} 完成 · ${p.tasksRunning} 进行 · ${p.hoursActual}h</div>
              ${hl ? `<div class="perf-hl">${hl.text}</div>` : ""}
            </div>
            <div class="perf-score">${p.outputScore}</div>
          </div>`;
        }).join("")}
      </div>
    </div>
    <p class="hint">由 ${author?.name || "CEO"} 汇总 · ${new Date(wr.generatedAt).toLocaleString("zh-CN")} · 部门细节按需展开，不强制五份长周报</p>`;
}

function exportWeeklyPdf() {
  const wr = data.weeklyReport;
  if (!wr || !window.jspdf) return;
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const margin = 48;
  let y = margin;
  const addLine = (text, bold = false, size = 10) => {
    if (y > 760) { doc.addPage(); y = margin; }
    doc.setFont("helvetica", bold ? "bold" : "normal");
    doc.setFontSize(size);
    doc.splitTextToSize(text, 515).forEach((line) => { doc.text(line, margin, y); y += size + 4; });
    y += 4;
  };
  addLine(`OPC Studio CEO 周报 ${wr.week}`, true, 14);
  addLine(wr.period);
  addLine(`摘要：${wr.summary}`);
  wr.sections.forEach((s) => { addLine(s.title, true, 11); addLine(s.content.replace(/[#*]/g, "")); });
  doc.save(`weekly_${wr.week}.pdf`);
}

function exportWeeklyMd() {
  const wr = data.weeklyReport;
  if (!wr) return;
  const md = `# OPC Studio 周报 ${wr.week}\n\n${wr.period}\n\n## 摘要\n${wr.summary}\n\n${wr.sections.map((s) => `## ${s.title}\n${s.content}`).join("\n\n")}\n\n---\n生成：${wr.generatedAt}`;
  downloadBlob(md, `weekly_${wr.week}.md`, "text/markdown;charset=utf-8");
}

function sendWeeklyMock() {
  if (data.weeklyReport.status === "sent") return;
  data.weeklyReport.status = "sent";
  data.inbox.filter((i) => i.weeklyReportId).forEach((i) => { i.read = true; i.status = "done"; });
  const ceo = getRole("ceo");
  if (ceo?.extras) ceo.extras.reportStatus = "本周周报已发送";
  updateBadges();
  renderInbox();
  renderWeekly();
  openModal(`<h2 style="font-size:1rem;font-weight:700">周报已发送</h2><p style="font-size:0.82rem;color:var(--text2);margin-top:0.5rem">Mock：已通过飞书推送给 Founder</p><button class="btn-primary" style="width:100%;margin-top:1rem" onclick="closeModal()">好的</button>`);
}

function openSettings() {
  openModal(`
    <h2 style="font-size:1.1rem;font-weight:700;margin-bottom:1rem">设置</h2>
    <div class="config-grid">
      ${data.roleConfig.map((cfg) => {
        const r = getRole(cfg.roleId);
        return `
        <button class="role-cost-row glass" style="margin-bottom:0.4rem" onclick="showRoleConfig('${cfg.roleId}')">
          <img src="../../assets/avatars/${cfg.roleId}.png" alt="" style="width:32px;height:32px"/>
          <div class="info"><div class="name">${r?.name}</div><div class="art-meta">${cfg.model}</div></div>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;opacity:0.4"><path d="M9 18l6-6-6-6"/></svg>
        </button>`;
      }).join("")}
    </div>
    <div class="modal-section">
      <div class="modal-section-title">渠道</div>
      <div class="channel-bar" style="margin-top:0.5rem">
        <div class="channel-pill on">${data.channels.feishu.label}</div>
        <div class="channel-pill on">${data.channels.wechat.label}</div>
      </div>
    </div>
  `, "wide");
}

window.showRoleModal = showRoleModal;
window.showStatsModal = showStatsModal;
window.showClientDetail = showClientDetail;
window.showProjectPnL = showProjectPnL;
window.setPnlFilter = setPnlFilter;
window.openWorkroom = openWorkroom;
window.selectArtifact = selectArtifact;
window.setInboxFilter = setInboxFilter;
window.setInboxStatusFilter = setInboxStatusFilter;
window.openInboxItem = openInboxItem;
window.approveHitl = approveHitl;
window.rejectHitl = rejectHitl;
window.resolveRequest = resolveRequest;
window.closeModal = closeModal;
window.exportCurrentMd = exportCurrentMd;
window.exportCurrentPdf = exportCurrentPdf;
window.exportProjectZip = exportProjectZip;
window.exportClientDeliveryZip = exportClientDeliveryZip;
window.exportWeeklyMd = exportWeeklyMd;
window.exportWeeklyPdf = exportWeeklyPdf;
window.sendWeeklyMock = sendWeeklyMock;
window.goToWeekly = goToWeekly;
window.showRoleConfig = showRoleConfig;

init().catch(() => {
  document.body.innerHTML = '<div style="padding:2rem;text-align:center;font-family:-apple-system,sans-serif"><p>请运行</p><code>cd ~/Documents/opc-agent-framework && python3 -m http.server 8765</code></div>';
});
