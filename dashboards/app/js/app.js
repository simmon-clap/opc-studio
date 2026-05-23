const BRAND_NAME = "Golden Mean Studio";

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
  reminder: "提醒",
  digest: "摘要",
  profile_suggestion: "偏好",
  proposal: "建议",
  handoff: "交接",
};

let data = null;
let roleConfigs = [];
let settingsRoleId = "ceo";
let runtimeSettings = null;
let inboxFilter = "all";
let inboxStatusFilter = "active";
let workroomProjectId = null;
let workroomArtifactId = null;
let openRoleId = null;
let syncTimer = null;
let lastSyncAt = 0;
let overviewResizeBound = false;
let orchestrationSSE = null;
let pulseSSE = null;
let lastPulseModules = null;
let seenDispatchIds = new Set();
let ceoTypingTimer = null;
let lastAnimatedCeoMsgId = null;
let dispatchBubbleTimer = null;
const SYNC_INTERVAL_MS = 15000;
const SYNC_FAST_MS = 8000;
const COLLAB_COLORS = ["#0071e3", "#34c759", "#ff9500", "#af52de", "#ff3b30"];

const CLIENT_STATUS = { active: "合作中", prospect: "洽谈", renewal: "续费", lead: "线索" };
const CLOSURE_STATUS = { awaiting_hitl: "待 HITL", in_closure: "结项中", closed: "已结项" };
const PNL_HEALTH = { healthy: "盈利", strong: "高毛利", watch: "需关注", pipeline: "线索", loss: "亏损" };

function applyBrandMeta() {
  const company = data?.meta?.company || BRAND_NAME;
  document.getElementById("company-name").textContent = company;
  document.title = company;
  const taglineEl = document.getElementById("company-tagline");
  if (taglineEl) taglineEl.textContent = data?.meta?.tagline || "";
}

async function init() {
  probeApiCapabilities();
  data = await loadDashboard();
  lastSyncAt = Date.now();
  applyBrandMeta();
  renderAll();
  bindNav();
  bindModal();
  bindSheet();
  document.getElementById("fab-ceo").onclick = () => { openCeoOffice(); };
  bindOverviewResize();
  ensurePulseStream();
  startLiveSync();
}

function ensurePulseStream() {
  if (pulseSSE || typeof EventSource === "undefined") return;
  pulseSSE = new EventSource(`${API_BASE}/pulse/stream`);
  pulseSSE.onmessage = async (ev) => {
    try {
      const payload = JSON.parse(ev.data);
      await handlePulseStream(payload);
    } catch (_) {}
  };
  pulseSSE.onerror = () => {
    pulseSSE?.close();
    pulseSSE = null;
    setTimeout(ensurePulseStream, 8000);
  };
}

/** @deprecated fallback — pulse/stream replaces this */
function ensureOrchestrationStream() {
  ensurePulseStream();
}

async function handlePulseStream(payload) {
  const modules = payload?.modules || {};
  const prev = lastPulseModules || {};
  lastPulseModules = modules;

  const needPresentation =
    modules.presentation?.changed ||
    modules.presentation?.sig !== prev.presentation?.sig ||
    modules.orchestration?.sig !== prev.orchestration?.sig;
  const needInbox =
    modules.inbox?.changed || modules.inbox?.sig !== prev.inbox?.sig;
  const needExecution =
    modules.execution?.changed || modules.execution?.sig !== prev.execution?.sig;

  if (!needPresentation && !needInbox && !needExecution) return;

  await refreshDashboard();
  lastSyncAt = Date.now();
  applyBrandMeta();

  const weeklyInteractive = typeof isWeeklyUiInteractive === "function" && isWeeklyUiInteractive();
  const financeInteractive = typeof isFinanceUiInteractive === "function" && isFinanceUiInteractive();
  const view = getActiveViewId();
  if (weeklyInteractive || financeInteractive) {
    updateBadges();
  } else if (needPresentation && view === "overview") {
    renderOverview();
  } else if (needPresentation || needInbox) {
    renderActiveView();
  } else if (needExecution) {
    updateBadges();
    if (view === "projects") renderProjects();
  } else {
    updateBadges();
  }

  if (openRoleId && !document.getElementById("modal-backdrop").hidden) {
    renderRoleModal(openRoleId);
  }
  if (document.querySelector(".ceo-office")) {
    updateCeoThreadPane();
  }
  if (workroomProjectId && !document.getElementById("sheet-backdrop").hidden) {
    if (typeof isWorkroomUiInteractive === "function" && isWorkroomUiInteractive()) {
      if (typeof loadWorkroomData === "function") await loadWorkroomData(workroomProjectId);
    } else {
      await syncWorkroomAfterRefresh();
    }
  }
}

function bindOverviewResize() {
  if (overviewResizeBound) return;
  overviewResizeBound = true;
  window.addEventListener("resize", () => {
    if (getActiveViewId() === "overview") {
      drawLines(document.getElementById("collab-svg"));
    }
  });
}

function getActiveViewId() {
  return document.querySelector(".nav-item.active")?.dataset?.view || "overview";
}

function isSyncFast() {
  const modalOpen = !document.getElementById("modal-backdrop").hidden;
  const sheetOpen = !document.getElementById("sheet-backdrop").hidden;
  const onOverview = getActiveViewId() === "overview";
  return modalOpen || sheetOpen || !!document.querySelector(".ceo-office") || onOverview;
}

function startLiveSync() {
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) tickLiveSync();
    else if (syncTimer) clearTimeout(syncTimer);
  });
  scheduleLiveSync();
}

function scheduleLiveSync() {
  if (syncTimer) clearTimeout(syncTimer);
  if (document.hidden) return;
  syncTimer = setTimeout(tickLiveSync, isSyncFast() ? SYNC_FAST_MS : SYNC_INTERVAL_MS);
}

async function tickLiveSync() {
  if (pulseSSE && Date.now() - lastSyncAt < SYNC_INTERVAL_MS - 1000) {
    scheduleLiveSync();
    return;
  }
  try {
    await refreshDashboard();
    lastSyncAt = Date.now();
    applyBrandMeta();
    const weeklyInteractive = typeof isWeeklyUiInteractive === "function" && isWeeklyUiInteractive();
    const financeInteractive = typeof isFinanceUiInteractive === "function" && isFinanceUiInteractive();
    if (weeklyInteractive || financeInteractive) {
      updateBadges();
    } else {
      renderActiveView();
    }
    if (openRoleId && !document.getElementById("modal-backdrop").hidden) {
      renderRoleModal(openRoleId);
    }
    if (document.querySelector(".ceo-office")) {
      updateCeoThreadPane();
    }
    if (workroomProjectId && !document.getElementById("sheet-backdrop").hidden) {
      if (typeof isWorkroomUiInteractive === "function" && isWorkroomUiInteractive()) {
        if (typeof loadWorkroomData === "function") await loadWorkroomData(workroomProjectId);
      } else {
        await syncWorkroomAfterRefresh();
      }
    }
  } catch (_) {
    /* offline / server restarting */
  } finally {
    scheduleLiveSync();
  }
}

function renderActiveView() {
  updateBadges();
  const view = getActiveViewId();
  switch (view) {
    case "overview":
      renderOverview();
      break;
    case "projects":
      renderProjects();
      break;
    case "clients":
      renderClients();
      break;
    case "inbox":
      renderInbox();
      break;
    case "costs":
      renderCosts();
      break;
    case "weekly":
      renderWeekly();
      break;
    case "settings":
      renderSettings();
      break;
    default:
      renderOverview();
  }
}

function renderAll() {
  updateBadges();
  renderOverview();
  renderProjects();
  renderClients();
  renderInbox();
  renderCosts();
  renderWeekly();
}

function updateBadges() {
  const unread = data.inbox.filter((i) => !i.read && (i.status || "active") === "active").length;
  document.getElementById("inbox-badge").textContent = unread;
  const weeklyBadge = document.getElementById("weekly-badge");
  if (weeklyBadge) {
    const draft = (data.weeklyReports || []).some((r) => r.status === "draft")
      || data.weeklyReport?.status === "draft";
    weeklyBadge.hidden = !draft;
    weeklyBadge.textContent = draft ? "1" : "0";
  }
}

async function goToView(viewId) {
  document.querySelectorAll(".nav-item").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === viewId);
  });
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.getElementById(`view-${viewId}`)?.classList.add("active");
  try {
    await refreshDashboard();
  } catch (_) {}
  renderActiveView();
  if (viewId === "overview") requestAnimationFrame(() => drawLines(document.getElementById("collab-svg")));
  if (viewId === "settings") loadSettingsView();
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

function showRoleModalStacked(roleId) {
  openRoleId = roleId;
  const backdrop = document.getElementById("modal-backdrop");
  refreshDashboard()
    .then(() => {
      renderRoleModal(roleId);
      backdrop.classList.add("modal-stacked");
      backdrop.hidden = false;
      document.body.style.overflow = "hidden";
    })
    .catch(() => {
      renderRoleModal(roleId);
      backdrop.classList.add("modal-stacked");
      backdrop.hidden = false;
    });
}

function closeModal() {
  const backdrop = document.getElementById("modal-backdrop");
  backdrop.hidden = true;
  backdrop.classList.remove("modal-stacked");
  document.body.style.overflow = document.getElementById("sheet-backdrop")?.hidden ? "" : "hidden";
  openRoleId = null;
  if (typeof weeklyDetailId !== "undefined") weeklyDetailId = null;
  if (typeof financeDetailProjectId !== "undefined") financeDetailProjectId = null;
  const closeBtn = document.getElementById("modal-close");
  if (closeBtn) closeBtn.hidden = false;
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

const KNOWN_AVATAR_ROLES = new Set(["ceo", "product", "legal", "dev", "ops"]);
function avatarSrc(roleId) {
  const id = KNOWN_AVATAR_ROLES.has(roleId) ? roleId : "ceo";
  return `../../assets/avatars/${id}.png`;
}
function avatarLabel(roleId) {
  if (roleId === "founder") return "Founder";
  return getRole(roleId)?.name || roleId;
}
function getClient(id) { return data.clients?.find((c) => c.id === id); }
function getArtifact(id) { return data.artifacts.find((a) => a.id === id); }
function getClosure(projectId) { return data.closure?.[projectId]; }
function getProjectPnL(projectId) { return data.costs?.byProject?.find((r) => r.projectId === projectId); }
function getProjectPnLRows() { return (data.costs?.byProject || []).filter((r) => r.projectId !== "_internal" && r.revenue != null); }
function getRoleTasks(roleId, status) { return data.tasks.filter((t) => t.roleId === roleId && t.status === status); }
function sortRoleTasksByRecency(tasks) {
  return [...tasks].sort((a, b) => {
    const key = (t) => t.completedAt || t.startedAt || t.id || "";
    return key(b).localeCompare(key(a));
  });
}
function getRoleTasksSorted(roleId, status) {
  return sortRoleTasksByRecency(getRoleTasks(roleId, status));
}
function getRoleTasksDoneRecent(roleId, limit = 5) {
  return getRoleTasksSorted(roleId, "done").slice(0, limit);
}
function fmtMoney(n) { return `¥${(n || 0).toLocaleString()}`; }

function channelBadge(ch) {
  const c = data.channels[ch];
  if (!c) return `<span class="channel-badge channel-web">${ch}</span>`;
  return `<span class="channel-badge channel-${ch}">${c.label}</span>`;
}

function progressRing(pct, size = 44, sw = 3, tone = "") {
  const r = (size - sw) / 2;
  const c = 2 * Math.PI * r;
  const off = c - (pct / 100) * c;
  const cls = tone ? ` progress-ring-${tone}` : "";
  return `<svg class="progress-ring${cls}" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle class="bg" cx="${size/2}" cy="${size/2}" r="${r}"/>
    <circle class="fg" cx="${size/2}" cy="${size/2}" r="${r}" stroke-dasharray="${c}" stroke-dashoffset="${off}"/>
  </svg>`;
}

function assigneeAvatars(ids, max = 4) {
  const html = ids.slice(0, max).map((id) => {
    const r = getRole(id);
    return r ? `<img src="${avatarSrc(id)}" alt="${escapeAttr(r.name)}" title="${escapeAttr(r.name)}"/>` : "";
  }).join("");
  const more = ids.length > max ? `<span class="more">+${ids.length - max}</span>` : "";
  return `<div class="assignees">${html}${more}</div>`;
}

/** 可点击头像（工作室等）；用 span 避免嵌套在 button 内破坏 DOM */
function assigneeAvatarsInteractive(ids, max = 4, size = 22) {
  const html = ids.slice(0, max).map((id) => {
    const r = getRole(id);
    if (!r) return "";
    return `<span class="avatar-hit" style="width:${size}px;height:${size}px" role="button" tabindex="0" title="${escapeAttr(r.name)}" onclick="event.stopPropagation();showRoleModalStacked('${id}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();showRoleModalStacked('${id}')}"><img src="${avatarSrc(id)}" alt="${escapeAttr(r.name)}"/></span>`;
  }).join("");
  const more = ids.length > max ? `<span class="more">+${ids.length - max}</span>` : "";
  return `<div class="assignees assignees-sm">${html}${more}</div>`;
}

function formatChatMessage(text) {
  return Presentation.renderMessageContent({ text });
}

function getOverviewLive() {
  return Presentation.getOverview(data);
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
function fmtSyncAgo(ts) {
  if (!ts) return "尚未同步";
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 5) return "刚刚更新";
  if (s < 60) return `${s} 秒前更新`;
  return `${Math.floor(s / 60)} 分钟前更新`;
}

function renderPulse() {
  const p = data.pulse;
  const alert = data.alerts?.[0];
  const el = document.getElementById("pulse-bar");
  if (!el || !p) return;
  const openCmts = (data.commitments || []).filter((c) => c.status === "open").length;
  const runningTasks = (data.tasks || []).filter((t) => t.status === "running").length;
  el.innerHTML = `
    <div class="pulse-item"><span class="pulse-val">${p.activeProjects}</span><span class="pulse-lbl">进行中</span></div>
    <div class="pulse-divider"></div>
    <div class="pulse-item ${p.hitlPending ? "warn" : ""}"><span class="pulse-val">${p.hitlPending}</span><span class="pulse-lbl">待批</span></div>
    <div class="pulse-divider"></div>
    <div class="pulse-item ${runningTasks ? "live" : ""}"><span class="pulse-val">${runningTasks}</span><span class="pulse-lbl">执行中</span></div>
    <div class="pulse-divider"></div>
    <div class="pulse-item"><span class="pulse-val">${p.leads}</span><span class="pulse-lbl">线索</span></div>
    ${openCmts ? `<div class="pulse-divider"></div><div class="pulse-item warn"><span class="pulse-val">${openCmts}</span><span class="pulse-lbl">承诺</span></div>` : ""}
    <div class="pulse-divider"></div>
    <div class="pulse-item ${p.alerts ? "alert" : ""}"><span class="pulse-val">${p.alerts}</span><span class="pulse-lbl">告警</span></div>
    ${alert ? `<div class="pulse-banner">${alert.message}</div>` : ""}`;
}

function getProjectCollaborations() {
  if (!data?.projects || !data?.roles) return [];
  return data.projects
    .map((proj) => {
      const activeRoles = data.roles.filter(
        (r) =>
          (proj.assignees || []).includes(r.id)
          && r.workStatus !== "idle"
          && (r.projectIds || []).includes(proj.id)
      );
      if (activeRoles.length < 2) return null;
      return {
        projectId: proj.id,
        clientName: (proj.clientName || proj.id).replace("（线索）", ""),
        roleIds: activeRoles.map((r) => r.id),
      };
    })
    .filter(Boolean);
}

function renderOverviewCollabPanel() {
  const el = document.getElementById("overview-collab");
  if (!el) return;
  const collabs = getProjectCollaborations();
  if (!collabs.length) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  el.innerHTML = `
    <div class="overview-collab-head">项目协作</div>
    ${collabs.map((c, i) => `
      <button type="button" class="overview-collab-row" onclick="openWorkroom('${c.projectId}')">
        <span class="collab-dot" style="background:${COLLAB_COLORS[i % COLLAB_COLORS.length]}"></span>
        <span class="collab-name">${escapeAttr(c.clientName)}</span>
        <span class="collab-roles">${c.roleIds.map((id) => ROLE_SHORT[id] || id).join(" · ")}</span>
        <span class="collab-go">工作室 →</span>
      </button>`).join("")}`;
}

function renderOverviewFooter() {
  const el = document.getElementById("overview-footer");
  if (!el) return;
  const working = data.roles.filter((r) => r.workStatus === "working").length;
  const waiting = data.roles.filter((r) => r.workStatus === "waiting").length;
  const collabs = getProjectCollaborations().length;
  el.innerHTML = `
    <span class="sync-dot" aria-hidden="true"></span>
    <span>${fmtSyncAgo(lastSyncAt)} · 每 ${isSyncFast() ? 2 : 5} 秒刷新</span>
    <span class="overview-footer-sep">·</span>
    <span>${working} 工作中 · ${waiting} 等待 · ${collabs} 项协作</span>`;
}

function renderOrchestrationBanner() {
  const el = document.getElementById("orchestration-banner");
  if (!el) return;
  const active = !!data?.meta?.orchestrationActive;
  const running = (data?.tasks || []).filter((t) => t.status === "running").length;
  if (!active && running === 0) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  el.innerHTML = active
    ? `<span class="orch-pulse"></span><strong>CEO 编排进行中</strong><span>Agent 正在派活与执行 · ${running} 个任务运行中</span>`
    : `<span class="orch-pulse idle"></span><span>${running} 个任务执行中 · 概览实时更新</span>`;
}

const DISPATCH_MAX_VISIBLE = 5;
const DISPATCH_TTL_MS = { assign: 14000, reply: 14000, deliver: 8000, fail: 10000 };
const DISPATCH_FADE_MS = 2500;

/** Canonical overview dialogues — derived on backend from tasks + feed. */
function getLiveDialogues() {
  const now = Date.now();
  const live = getOverviewLive();
  const items = live?.dialogues;
  if (Array.isArray(items)) {
    return items.filter((item) => {
      if (!item.visibleUntil) return true;
      return new Date(item.visibleUntil).getTime() + DISPATCH_FADE_MS > now;
    }).slice(0, DISPATCH_MAX_VISIBLE);
  }
  return legacyVisibleDispatchFeed();
}

function liveDialogueOpacity(item) {
  if (!item.visibleUntil) return 1;
  const left = new Date(item.visibleUntil).getTime() - Date.now();
  if (left <= 0) return 0;
  if (left >= DISPATCH_FADE_MS) return 1;
  return Math.max(0, left / DISPATCH_FADE_MS);
}

function bubbleAnchorFromItem(item) {
  if (item.anchor === "edge") {
    const from = ROLE_POS[item.edgeFrom || item.speakerRole];
    const to = ROLE_POS[item.edgeTo || item.peerRole];
    if (from && to) {
      return { left: (from.x + to.x) / 2, top: (from.y + to.y) / 2 - 6 };
    }
  }
  const speaker = ROLE_POS[item.speakerRole];
  if (!speaker) return { left: 50, top: 50 };
  const slot = item.slot || 0;
  return { left: speaker.x, top: Math.min(speaker.y + 14 + slot * 10, 88) };
}

function renderDispatchBubbles() {
  const root = document.getElementById("dispatch-bubbles");
  if (!root) return;
  const feed = getLiveDialogues();
  if (!feed.length) {
    root.innerHTML = "";
    return;
  }
  root.innerHTML = feed.map((item) => {
    const speaker = getRole(item.speakerRole);
    const anchor = bubbleAnchorFromItem(item);
    const isNew = !seenDispatchIds.has(item.id);
    if (isNew) seenDispatchIds.add(item.id);
    const opacity = liveDialogueOpacity(item);
    const tailClass = item.anchor === "edge" ? "tail-mid" : "tail-speaker";
    return `
      <div class="dispatch-bubble tone-${item.tone} ${tailClass}${isNew ? " is-new" : ""}"
        style="left:${anchor.left}%;top:${anchor.top}%;opacity:${opacity.toFixed(2)}"
        title="${escapeAttr(item.text)}">
        <div class="bubble-speaker">
          <img src="../../assets/avatars/${item.speakerRole}.png" alt=""/>
          <span>${speaker?.name || ROLE_SHORT[item.speakerRole] || item.speakerRole}</span>
        </div>
        <div class="bubble-text">${escapeAttr(item.text)}</div>
      </div>`;
  }).join("");
}

/** Legacy fallback when overviewLive is absent (old cached payloads). */
function normalizeDispatchItem(item) {
  const toneMap = { assign: "assign", accept: "reply", complete: "deliver", fail: "fail" };
  const tone = item.tone || toneMap[item.kind] || "reply";
  const speakerRole = item.speakerRole
    || (tone === "assign" ? item.fromRole : item.toRole || item.fromRole);
  const peerRole = item.peerRole || item.toRole || item.fromRole || speakerRole;
  const text = item.text || item.message || "";
  return { ...item, tone, speakerRole, peerRole, text };
}

function legacyDispatchMatchesTask(item) {
  const taskId = item.taskId;
  if (!taskId) return false;
  const task = (data?.tasks || []).find((t) => t.id === taskId);
  if (!task) return false;
  if (item.tone === "assign") return task.status === "pending";
  if (item.tone === "reply") return task.status === "running";
  return false;
}

function legacyDispatchVisibleByAge(item) {
  const age = Date.now() - new Date(item.at || 0).getTime();
  const ttl = DISPATCH_TTL_MS[item.tone] || 12000;
  return age < ttl + DISPATCH_FADE_MS;
}

function legacyVisibleDispatchFeed() {
  return (data?.dispatchFeed || [])
    .map(normalizeDispatchItem)
    .filter((item) => legacyDispatchMatchesTask(item))
    .filter((item) => legacyDispatchVisibleByAge(item))
    .slice(0, DISPATCH_MAX_VISIBLE);
}

function renderOverview() {
  renderPulse();
  renderOrchestrationBanner();
  document.getElementById("role-nodes").innerHTML = data.roles.map((r) => {
    const pos = ROLE_POS[r.id];
    return `
      <div class="role-node" style="left:${pos.x}%;top:${pos.y}%" onclick="showRoleModal('${r.id}')" role="button" title="${escapeAttr(r.focus || STATUS_LABEL[r.workStatus] || "")}">
        <div class="avatar-wrap">
          <div class="status-ring ${r.workStatus}"></div>
          <img src="../../assets/avatars/${r.id}.png" alt="${r.name}"/>
          <div class="status-icon ${r.workStatus}">${STATUS_SVG[r.workStatus]}</div>
        </div>
        <span class="name">${r.name}</span>
        <span class="role-label">${ROLE_SHORT[r.id]}</span>
      </div>`;
  }).join("");
  renderDispatchBubbles();
  renderOverviewCollabPanel();
  renderOverviewFooter();
  scheduleDispatchBubbleRefresh();
  requestAnimationFrame(() => drawLines(document.getElementById("collab-svg")));
}

function scheduleDispatchBubbleRefresh() {
  if (dispatchBubbleTimer) clearInterval(dispatchBubbleTimer);
  if (getActiveViewId() !== "overview") return;
  dispatchBubbleTimer = setInterval(() => {
    if (getActiveViewId() !== "overview") {
      clearInterval(dispatchBubbleTimer);
      dispatchBubbleTimer = null;
      return;
    }
    if (getLiveDialogues().length) renderDispatchBubbles();
  }, 400);
}

function drawLines(svg) {
  const stage = document.getElementById("overview-stage");
  if (!stage || !svg) return;
  const rect = stage.getBoundingClientRect();
  svg.setAttribute("viewBox", `0 0 ${rect.width} ${rect.height}`);
  svg.innerHTML = "";
  const live = getOverviewLive();
  const liveEdgeKeys = new Set(
    (live?.activeEdges || []).map((e) => `${e.fromRole}:${e.toRole}`)
  );
  getProjectCollaborations().forEach((collab, idx) => {
    const color = COLLAB_COLORS[idx % COLLAB_COLORS.length];
    const roles = collab.roleIds;
    for (let i = 0; i < roles.length; i++) {
      for (let j = i + 1; j < roles.length; j++) {
        const key = `${roles[i]}:${roles[j]}`;
        const rev = `${roles[j]}:${roles[i]}`;
        const live = liveEdgeKeys.has(key) || liveEdgeKeys.has(rev);
        drawCollabEdge(svg, rect, roles[i], roles[j], collab, color, live);
      }
    }
  });
  (getOverviewLive()?.activeEdges || []).forEach((edge) => {
    if (!ROLE_POS[edge.fromRole] || !ROLE_POS[edge.toRole]) return;
    drawLiveEdge(svg, rect, edge.fromRole, edge.toRole, edge.tone);
  });
}

function drawCollabEdge(svg, rect, roleA, roleB, collab, color, live = false) {
  const pa = ROLE_POS[roleA];
  const pb = ROLE_POS[roleB];
  if (!pa || !pb) return;
  const x1 = (pa.x / 100) * rect.width;
  const y1 = (pa.y / 100) * rect.height;
  const x2 = (pb.x / 100) * rect.width;
  const y2 = (pb.y / 100) * rect.height;
  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  g.style.cursor = "pointer";
  g.setAttribute("data-project-id", collab.projectId);
  g.onclick = () => openWorkroom(collab.projectId);
  const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
  line.setAttribute("x1", x1);
  line.setAttribute("y1", y1);
  line.setAttribute("x2", x2);
  line.setAttribute("y2", y2);
  line.setAttribute("stroke", live ? "#0071e3" : color);
  line.setAttribute("stroke-width", live ? "3" : "2");
  line.setAttribute("stroke-opacity", live ? "0.85" : "0.35");
  line.setAttribute("stroke-dasharray", live ? "8 4" : "6 4");
  if (live) line.classList.add("edge-live");
  line.style.pointerEvents = "stroke";
  const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
  title.textContent = `${collab.clientName} · ${ROLE_SHORT[roleA] || roleA} ↔ ${ROLE_SHORT[roleB] || roleB}`;
  g.appendChild(title);
  g.appendChild(line);
  svg.appendChild(g);
}

function drawLiveEdge(svg, rect, roleA, roleB, tone) {
  const pa = ROLE_POS[roleA];
  const pb = ROLE_POS[roleB];
  if (!pa || !pb) return;
  const x1 = (pa.x / 100) * rect.width;
  const y1 = (pa.y / 100) * rect.height;
  const x2 = (pb.x / 100) * rect.width;
  const y2 = (pb.y / 100) * rect.height;
  const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
  line.setAttribute("x1", x1);
  line.setAttribute("y1", y1);
  line.setAttribute("x2", x2);
  line.setAttribute("y2", y2);
  line.setAttribute("stroke", tone === "assign" ? "#ff9500" : "#0071e3");
  line.setAttribute("stroke-width", "3.5");
  line.setAttribute("stroke-opacity", "0.9");
  line.setAttribute("stroke-dasharray", "10 5");
  line.classList.add("edge-live");
  line.style.pointerEvents = "none";
  svg.appendChild(line);
}

function showRoleModal(roleId) {
  openRoleId = roleId;
  refreshDashboard()
    .then(() => renderRoleModal(roleId))
    .catch(() => renderRoleModal(roleId));
}

function renderRoleModal(roleId) {
  const r = getRole(roleId);
  if (!r) return;
  const running = getRoleTasksSorted(roleId, "running");
  const pending = getRoleTasksSorted(roleId, "pending");
  const doneRecent = getRoleTasksDoneRecent(roleId, 5);
  const extras = r.extras ? Object.entries(r.extras).map(([k, v]) => {
    if (k === "taskRunning" || k === "taskPending") return "";
    const label = {
      decisionQueue: "决策队列",
      riskAlerts: "风险",
      reportStatus: "周报",
      prdProgress: "PRD",
      openQuestions: "待澄清",
      quotesPending: "待报价",
      complianceFlags: "合规",
      environment: "环境",
      selfTest: "自测",
      tokenUsageMock: "Token",
      pipelineChanges: "Pipeline",
      draftsPending: "草稿",
      taskDoneRecent: "近期完成",
      hitlPending: "待批项目",
      openLeads: "线索数",
      prdRunning: "PRD 任务",
      pipelineLeads: "Pipeline 线索",
    }[k] || k;
    if (v == null || v === "" || (Array.isArray(v) && !v.length)) return "";
    const val = Array.isArray(v) ? v.join(" · ") : v;
    return `<div class="config-row"><span class="k">${label}</span><span>${val}</span></div>`;
  }).filter(Boolean).join("") : "";

  const TASK_STATUS = { running: "执行中", pending: "排队", done: "已完成", blocked: "阻塞" };

  const taskCard = (t, done = false) => {
    const proj = getProject(t.projectId);
    const client = proj?.clientName?.replace("（线索）", "") || "";
    const shortTitle = (t.title || "任务").includes(" · ")
      ? t.title.split(" · ").slice(-1)[0]
      : t.title;
    const acts = (t.activities || []).slice(-2).map((a) =>
      `<div class="activity-row"><span class="activity-time">${fmtRelative(a.at)}</span><span>${escapeAttr(a.message)}</span></div>`
    ).join("");
    const waitHint = t.waitingOn
      ? `<div class="task-note">等待 ${t.waitingOn === "product" ? "产品" : t.waitingOn} · 依赖前置任务</div>`
      : t.dependsOn?.length
        ? `<div class="task-note">依赖前置任务完成后启动</div>`
        : "";
    return `
      <div class="task-card glass-inner${done ? " task-done" : ""}">
        <div class="task-card-head">
          <div class="task-card-title">
            <div class="t">${escapeAttr(shortTitle)}</div>
            ${client ? `<div class="task-project-tag">${escapeAttr(client)}</div>` : ""}
          </div>
          <span class="task-status-pill status-${t.status || "running"}">${done ? "已完成" : TASK_STATUS[t.status] || t.status}</span>
        </div>
        ${t.progressNote ? `<div class="task-note rich-text">${formatChatMessage(t.progressNote)}</div>` : ""}
        ${waitHint}
        ${acts ? `<div class="activity-list">${acts}</div>` : ""}
        ${done && t.completedAt ? `<div class="task-done-at">${new Date(t.completedAt).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}</div>` : ""}
      </div>`;
  };

  const taskBlock = (tasks, title, done = false) => {
    if (!tasks.length) return "";
    const byProject = {};
    tasks.forEach((t) => {
      const key = t.projectId || "other";
      byProject[key] = byProject[key] || [];
      byProject[key].push(t);
    });
    const groups = Object.entries(byProject).map(([pid, list]) => {
      const proj = getProject(pid);
      const label = proj?.clientName?.replace("（线索）", "") || pid;
      return `
        <div class="task-project-group">
          ${Object.keys(byProject).length > 1 ? `<div class="task-group-label">${escapeAttr(label)}</div>` : ""}
          ${list.map((t) => taskCard(t, done)).join("")}
        </div>`;
    }).join("");
    return `
    <div class="modal-section">
      <div class="modal-section-title">${title} · ${tasks.length}</div>
      ${groups}
    </div>`;
  };

  const html = `
    <div class="modal-hero">
      <img src="../../assets/avatars/${r.id}.png" alt=""/>
      <div><h2>${r.name}</h2><div class="sub">${r.title}</div></div>
    </div>
    <div class="modal-stat-row">
      <div class="modal-stat"><div class="v">${r.load.current}/${r.load.max}</div><div class="l">负荷</div></div>
      <div class="modal-stat"><div class="v">${r.weeklyHours?.actual || 0}h</div><div class="l">本周</div></div>
      <div class="modal-stat"><div class="v">${STATUS_LABEL[r.workStatus] || r.workStatus}</div><div class="l">状态</div></div>
    </div>
    <div class="focus-line">${r.focus}</div>
    ${extras ? `<div class="config-grid" style="margin:0.75rem 0">${extras}</div>` : ""}
    ${taskBlock(running, "进行中")}
    ${taskBlock(pending, "排队中")}
    ${taskBlock(doneRecent, "近期完成", true)}
  `;

  const backdropOpen = !document.getElementById("modal-backdrop").hidden;
  if (backdropOpen && openRoleId === roleId) {
    document.getElementById("modal-body").innerHTML = html;
  } else {
    openModal(html, "wide");
  }
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
    const pd = p.progressDetail || {};
    const stageLabel = pd.stageShort || (p.stage || "").replace(/阶段\d · /, "") || "—";
    const execLine = pd.executionNote
      ? `<div class="stage-exec">${pd.executionNote.slice(0, 42)}${pd.executionNote.length > 42 ? "…" : ""}</div>`
      : pd.runningTaskCount
        ? `<div class="stage-exec">${pd.runningTaskCount} 项执行中</div>`
        : "";
    const ringPct = pd.executionProgress != null ? pd.executionProgress : (p.progress || 0);
    const tags = [
      pnl ? renderProjectPnLBadge(pnl) : "",
      p.hitlPending ? `<span class="project-tag tag-hitl">${p.hitlPending} 待批</span>` : "",
      closure && closure.status !== "closed"
        ? `<span class="project-tag tag-closure">${CLOSURE_STATUS[closure.status] || closure.status}</span>`
        : "",
    ].filter(Boolean);
    return `
    <button class="project-card glass${p.hitlPending ? " has-hitl" : ""}" onclick="openWorkroom('${p.id}')">
      <div class="project-top">
        <div class="project-name">${p.clientName.replace("（线索）", "")}</div>
        <span class="priority pri-${p.priority}">${p.priority}</span>
      </div>
      <div class="project-progress">
        ${progressRing(ringPct, 44, 3, p.hitlPending ? "warn" : "")}
        <div class="progress-meta">
          <div class="pct">${stageLabel}</div>
          <div class="stage">阶段 ${pd.stageIndex || "?"} · ${p.progress || 0}%</div>
          ${execLine}
        </div>
      </div>
      <div class="project-tags">${tags.join("") || '<span class="project-tag tag-empty">—</span>'}</div>
      <div class="project-footer">
        ${assigneeAvatars(p.assignees || [])}
        <span class="project-card-hint${artCount ? "" : " is-placeholder"}">
          ${artCount ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/></svg>${artCount} 份产出 · 进入工作室` : ""}
        </span>
      </div>
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
  if (workroomProjectId !== projectId) briefEditOpen = false;
  workroomProjectId = projectId;
  workroomArtifactId = artifactId || null;
  refreshDashboard()
    .then(() => renderWorkroomShell(projectId, artifactId))
    .catch(() => renderWorkroomShell(projectId, artifactId));
}

async function renderWorkroomShell(projectId, artifactId) {
  const p = getProject(projectId);
  if (!p) return;
  const ui = typeof captureWorkroomUiState === "function" ? captureWorkroomUiState() : null;
  const arts = sortRoleTasksByRecency(
    data.artifacts.filter((a) => a.projectId === projectId)
  );
  workroomArtifactId = artifactId || workroomArtifactId || (arts[0]?.id);

  document.getElementById("sheet-title").textContent = p.clientName.replace("（线索）", "");

  await loadWorkroomData(projectId);
  renderWorkroomHeader(
    workroomData?.header || {
      stage: p.stage,
      stageShort: (p.progressDetail?.stageShort) || (p.stage || "").replace(/阶段\d · /, ""),
      progress: p.progress,
      progressDetail: p.progressDetail || {},
      hitlPending: p.hitlPending,
      priority: p.priority,
      summary: p.summary,
      agentDeliverable: p.agentDeliverable,
      assignees: p.assignees || [],
      exportMenu: workroomData?.exportMenu || [{ id: "internal", label: "内部完整包 ZIP" }],
    }
  );
  document.getElementById("workroom-nav").innerHTML = renderWorkroomNavGrouped(
    projectId,
    workroomArtifactId,
    workroomData
  );
  renderWorkroomFocus(workroomData);
  renderWorkroomArtifactContent();
  if (typeof restoreWorkroomUiState === "function") restoreWorkroomUiState(ui);
  openSheet();
  requestAnimationFrame(() => {
    const el = document.getElementById("workroom-content");
    if (el) el.scrollTop = 0;
  });
}

function markClosureItem(projectId, itemId) {
  apiPatch(`/projects/${projectId}/closure/checklist/${itemId}`, { done: true })
    .then(() => refreshDashboard())
    .then(() => syncWorkroomAfterRefresh())
    .catch((e) => alert(`更新失败：${e.message}`));
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

async function exportCurrentPdf() {
  const art = getArtifact(workroomArtifactId);
  if (!art) return;
  const p = getProject(workroomProjectId);
  const kind = ART_KIND_LABELS[artifactKind(art)] || artifactKind(art);
  const node = buildPdfExportNode({
    title: `${p?.clientName || ""} — ${art.title}`,
    subtitle: `${kind || "文档"} · v${art.version || "0.1"}`,
    bodyHtml: simpleMarkdown(art.content || ""),
  });
  try {
    await exportHtmlToPdf(node, `${slugify(p?.clientName)}_${slugify(art.title)}.pdf`);
  } catch (e) {
    alert(`PDF 导出失败：${e.message}`);
  }
}

async function exportProjectZip() {
  const p = getProject(workroomProjectId);
  const name = `${slugify(p?.clientName)}_delivery.zip`;
  await downloadBlobFromApi(`/projects/${workroomProjectId}/export?type=internal`, name);
}

async function exportClientDeliveryZip() {
  const p = getProject(workroomProjectId);
  const name = `${slugify(p?.clientName)}_客户交付.zip`;
  await downloadBlobFromApi(`/projects/${workroomProjectId}/export?type=client`, name);
  await refreshDashboard();
  await syncWorkroomAfterRefresh();
}

function selectArtifact(id) {
  workroomArtifactId = id;
  workroomViewVersion = null;
  workroomSelectedFile = null;
  workroomDiffMode = false;
  workroomDiffFrom = null;
  workroomDiffTo = null;
  workroomDiffLines = null;
  workroomEditMode = false;
  workroomEditContent = null;
  const art = getArtifact(id);
  if (art) delete art._viewContent;
  document.querySelectorAll(".art-item").forEach((el) => el.classList.remove("active"));
  document.querySelector(`.art-item[data-artifact-id="${id}"]`)?.classList.add("active");
  renderWorkroomArtifactContent();
  const el = document.getElementById("workroom-content");
  if (el) el.scrollTop = 0;
}

/* ── Inbox (C + approvals) ── */
function renderInbox() {
  const filters = [
    { id: "all", label: "全部" },
    { id: "must_read", label: "必读" },
    { id: "request", label: "请示" },
    { id: "approval", label: "待批" },
    { id: "reminder", label: "提醒" },
    { id: "digest", label: "摘要" },
    { id: "profile_suggestion", label: "偏好" },
    { id: "proposal", label: "建议" },
  ];
  const statusFilters = [
    { id: "active", label: "待办" },
    { id: "done", label: "已办" },
    { id: "archived", label: "归档" },
  ];

  const countByCategory = (catId) =>
    data.inbox.filter((i) => (i.status || "active") === inboxStatusFilter && (catId === "all" || i.category === catId)).length;

  document.getElementById("inbox-filters").innerHTML = `
    <div class="inbox-toolbar glass-inner">
      <div class="inbox-filter-block">
        <span class="inbox-filter-label">办理状态</span>
        <div class="filter-chips">${statusFilters.map((f) => `
          <button type="button" class="filter-chip ${inboxStatusFilter === f.id ? "active" : ""}" onclick="setInboxStatusFilter('${f.id}')">${f.label}</button>
        `).join("")}</div>
      </div>
      <div class="inbox-filter-divider" aria-hidden="true"></div>
      <div class="inbox-filter-block">
        <span class="inbox-filter-label">消息类型</span>
        <div class="filter-chips">${filters.map((f) => {
          const n = countByCategory(f.id);
          return `<button type="button" class="filter-chip ${inboxFilter === f.id ? "active" : ""}" onclick="setInboxFilter('${f.id}')">${f.label}${n ? `<em class="chip-count">${n}</em>` : ""}</button>`;
        }).join("")}</div>
      </div>
    </div>`;

  const items = data.inbox.filter((i) => {
    const status = i.status || "active";
    if (status !== inboxStatusFilter) return false;
    return inboxFilter === "all" || i.category === inboxFilter;
  });

  document.getElementById("inbox-list").innerHTML = items.length ? items.map((item) => {
    const fromId = item.from || "ceo";
    return `
    <button type="button" class="inbox-card glass ${item.read ? "" : "unread"}" onclick="openInboxItem('${item.id}')">
      <img class="inbox-avatar" src="${avatarSrc(fromId)}" alt="${escapeAttr(avatarLabel(fromId))}"/>
      <div class="inbox-body">
        <div class="inbox-head">
          <h4>${item.title}</h4>
          <span class="inbox-time">${fmtRelative(item.at)}</span>
        </div>
        <p>${item.preview}</p>
        <div class="inbox-meta">
          <span class="cat-badge cat-${item.category}">${INBOX_CAT[item.category] || item.category}</span>
          ${channelBadge(item.channel)}
          ${item.resolution === "approved" ? '<span class="cat-badge resolved">已批准</span>' : ""}
          ${item.resolution === "rejected" ? '<span class="cat-badge rejected">已驳回</span>' : ""}
        </div>
      </div>
    </button>`;
  }).join("") : `<div class="empty-state glass inbox-empty"><p>${inboxStatusFilter === "active" ? "暂无待办消息" : "暂无记录"}</p><p class="inbox-empty-hint">${inboxFilter !== "all" ? "可切换「全部」或调整办理状态查看" : "新消息会出现在这里"}</p></div>`;

  const rejectEl = document.getElementById("inbox-reject");
  if (rejectEl) {
    const showReject = data.rejectHistory?.length && inboxStatusFilter === "active";
    rejectEl.hidden = !showReject;
    rejectEl.innerHTML = showReject ? `
      <div class="reject-history glass">
        <div class="reject-history-head">
          <span class="reject-history-title">近期驳回</span>
          <span class="reject-history-sub">审批未通过，便于回溯</span>
        </div>
        ${data.rejectHistory.map((r) => {
          const proj = getProject(r.projectId);
          return `<div class="reject-row"><span class="reject-type">${r.type}</span><span class="reject-note">${proj?.clientName || ""} · ${r.note}</span><span class="reject-at">${r.at}</span></div>`;
        }).join("")}
      </div>` : "";
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

async function openInboxItem(id) {
  const item = data.inbox.find((i) => i.id === id);
  if (!item) return;
  if (!item.read) {
    item.read = true;
    updateBadges();
    renderInbox();
    apiPatch(`/inbox/${id}`, { read: true }).catch(() => {});
  }

  if (item.category === "approval" && item.hitlId) {
    openHitlDetail(item.hitlId);
    return;
  }

  if (item.category === "proposal") {
    const prop = item.proposal || {};
    const ceoNote = prop.ceoNote
      ? `<p class="hint" style="margin-bottom:0.75rem">CEO 评估：${escapeAttr(prop.ceoNote)}</p>`
      : "";
    const canDispatch = prop.suggestedAction === "dispatch";
    openModal(`
      <div style="display:flex;gap:0.5rem;margin-bottom:0.75rem">${channelBadge(item.channel)}<span class="cat-badge cat-proposal">建议</span>${item.resolution === "auto_approved" ? '<span class="cat-badge resolved">已自动派活</span>' : ""}</div>
      <h2 style="font-size:1.05rem;font-weight:700">${item.title}</h2>
      <p style="font-size:0.82rem;color:var(--text2);margin:0.5rem 0 1rem;line-height:1.5">${item.preview}</p>
      ${ceoNote}
      <p style="font-size:0.72rem;color:var(--text3);margin-bottom:1rem">
        ${canDispatch ? `建议派给 <strong>${ROLE_SHORT[prop.suggestedRole] || prop.suggestedRole || "—"}</strong>：${prop.suggestedTitle || "—"}` : "建议审阅后再决定是否派活"}
      </p>
      <div class="btn-row">
        ${canDispatch ? `<button class="btn-primary" onclick="resolveProposal('${item.id}','approve')">采纳并派活</button>` : `<button class="btn-primary" onclick="resolveProposal('${item.id}','approve')">标记已阅</button>`}
        <button class="btn-secondary" onclick="resolveProposal('${item.id}','discuss')">暂不处理</button>
      </div>
    `, "wide");
    return;
  }

  if (item.category === "profile_suggestion" && item.profileSuggestionId) {
    const sug = (data.profileSuggestions || []).find((s) => s.id === item.profileSuggestionId);
    openModal(`
      <div style="display:flex;gap:0.5rem;margin-bottom:0.75rem">${channelBadge(item.channel)}<span class="cat-badge cat-profile_suggestion">偏好建议</span></div>
      <h2 style="font-size:1.05rem;font-weight:700">${item.title}</h2>
      <p style="font-size:0.82rem;color:var(--text2);margin:0.5rem 0 1rem;line-height:1.5">${sug?.note || item.preview}</p>
      <p style="font-size:0.72rem;color:var(--text3);margin-bottom:1rem">采纳后写入 Founder Profile 文档「已确认偏好」；忽略则不再提示。</p>
      <div class="btn-row">
        <button class="btn-primary" onclick="adoptProfileSuggestion('${item.profileSuggestionId}','${item.id}')">采纳偏好</button>
        <button class="btn-secondary" onclick="dismissProfileSuggestion('${item.profileSuggestionId}','${item.id}')">忽略</button>
      </div>
    `, "wide");
    return;
  }

  if (item.category === "reminder" || item.category === "digest") {
    openModal(`
      <div style="display:flex;gap:0.5rem;margin-bottom:0.75rem">${channelBadge(item.channel)}<span class="cat-badge cat-${item.category}">${INBOX_CAT[item.category]}</span></div>
      <h2 style="font-size:1.05rem;font-weight:700">${item.title}</h2>
      <p style="font-size:0.82rem;color:var(--text2);margin:0.5rem 0 1rem;line-height:1.5">${item.preview}</p>
      ${item.projectId ? `<button class="btn-secondary" style="width:100%" onclick="closeModal();openWorkroom('${item.projectId}')">进入项目工作室 →</button>` : `<button class="btn-secondary" style="width:100%;margin-top:0.5rem" onclick="closeModal()">知道了</button>`}
    `, "wide");
    return;
  }

  if (item.weeklyReportId || item.title.includes("周报")) {
    const wid = item.weeklyReportId || "2026-W20";
    openWeeklyDetail(wid);
    apiPatch(`/inbox/${item.id}`, { read: true }).catch(() => {});
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

async function resolveRequest(itemId, action) {
  await apiPost(`/inbox/${itemId}/resolve`, { action });
  closeModal();
  await refreshDashboard();
  renderAll();
}

async function resolveProposal(itemId, action) {
  await apiPost(`/inbox/${itemId}/resolve`, { action });
  closeModal();
  await refreshDashboard();
  renderAll();
}

async function adoptProfileSuggestion(suggestionId, inboxId) {
  try {
    await apiPost(`/founder/profile/suggestions/${suggestionId}/adopt`, {});
    if (inboxId) await apiPatch(`/inbox/${inboxId}`, { read: true, status: "done" }).catch(() => {});
    closeModal();
    await refreshDashboard();
    renderAll();
  } catch (e) {
    alert(`采纳失败：${e.message}`);
  }
}

async function dismissProfileSuggestion(suggestionId, inboxId) {
  try {
    await apiPost(`/founder/profile/suggestions/${suggestionId}/dismiss`, {});
    if (inboxId) await apiPatch(`/inbox/${inboxId}`, { read: true, status: "done" }).catch(() => {});
    closeModal();
    await refreshDashboard();
    renderAll();
  } catch (e) {
    alert(`忽略失败：${e.message}`);
  }
}

async function rejectHitl(id) {
  const note = document.getElementById("reject-note")?.value?.trim() || "需修改后重新提交";
  const item = data.hitlQueue.find((h) => h.id === id);
  if (!item || item.approved) return;
  await apiPost(`/hitl/${id}/reject`, { note });
  closeModal();
  await refreshDashboard();
  renderAll();
  if (workroomProjectId && !document.getElementById("sheet-backdrop").hidden) {
    if (typeof isWorkroomUiInteractive === "function" && isWorkroomUiInteractive()) {
      if (typeof loadWorkroomData === "function") await loadWorkroomData(workroomProjectId);
    } else {
      await syncWorkroomAfterRefresh();
    }
  }
}

async function approveHitl(id) {
  const item = data.hitlQueue.find((h) => h.id === id);
  if (!item || item.approved) return;
  const projectId = item.projectId;
  await apiPost(`/hitl/${id}/approve`, {});
  closeModal();
  await refreshDashboard();
  renderAll();
  if (workroomProjectId && !document.getElementById("sheet-backdrop").hidden) {
    if (typeof isWorkroomUiInteractive === "function" && isWorkroomUiInteractive()) {
      if (typeof loadWorkroomData === "function") await loadWorkroomData(workroomProjectId);
    } else {
      await syncWorkroomAfterRefresh();
    }
  }
  setTimeout(() => {
    openWorkroom(projectId);
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
function renderCeoThreadHtml(thread, typingText = null, typingMsgId = null, useRichText = true) {
  return thread
    .filter((m) => m.type === "ack" || (m.text || "").trim())
    .map((m) => {
      const isFounder = m.direction === "founder_to_ceo";
      const pending = m.type === "ack";
      let body = pending ? "…" : (m.text || "").trim();
      if (!pending && typingMsgId && m.id === typingMsgId && typingText != null) {
        body = typingText;
      }
      const inner = pending
        ? escapeAttr(body)
        : (isFounder || !useRichText ? escapeAttr(body) : Presentation.renderMessageContent(m));
      return `
      <div class="thread-msg ${isFounder ? "founder" : "ceo"}${pending ? " pending" : ""}">
        <div class="bubble rich-text">${inner}</div>
        <div class="bubble-meta">${channelBadge(m.channel)} · ${new Date(m.at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</div>
      </div>`;
    })
    .join("");
}

function scrollCeoThreadToBottom() {
  const el = document.querySelector(".ceo-office .thread");
  if (el) el.scrollTop = el.scrollHeight;
}

function updateCeoThreadPane(skipAnimate = false) {
  const el = document.querySelector(".ceo-office .thread");
  if (!el || !data?.ceoThread) return;
  el.innerHTML = renderCeoThreadHtml(data.ceoThread, null, null, false);
  scrollCeoThreadToBottom();
  if (skipAnimate) return;
  const last = [...(data.ceoThread || [])].reverse().find(
    (m) => m.direction === "ceo_to_founder" && m.type !== "ack" && (m.text || "").trim()
  );
  if (last && last.id !== lastAnimatedCeoMsgId && !isCeoThreadPending(data.ceoThread)) {
    animateCeoReply(last);
  }
}

async function animateCeoReply(msg) {
  if (!msg?.text || msg.type === "ack") return;
  if (lastAnimatedCeoMsgId === msg.id) return;
  lastAnimatedCeoMsgId = msg.id;
  const el = document.querySelector(".ceo-office .thread");
  if (!el) return;
  const full = msg.text.trim();
  const step = full.length > 280 ? 4 : full.length > 120 ? 2 : 1;
  for (let i = step; i <= full.length; i += step) {
    if (!document.querySelector(".ceo-office")) return;
    el.innerHTML = renderCeoThreadHtml(data.ceoThread, full.slice(0, i), msg.id, false);
    scrollCeoThreadToBottom();
    await sleep(full.length > 200 ? 12 : 22);
  }
  el.innerHTML = renderCeoThreadHtml(data.ceoThread, null, null, true);
  scrollCeoThreadToBottom();
}

function renderOpenCommitmentsHtml() {
  const open = (data?.commitments || []).filter((c) => c.status === "open").slice(0, 5);
  if (!open.length) return "";
  return `
    <div class="ceo-commitments glass-inner">
      <div class="ceo-commitments-head">待办承诺 · ${open.length}${(data.commitments || []).filter((c) => c.status === "open").length > 5 ? "+" : ""}</div>
      ${open.map((c) => {
        const proj = getProject(c.projectId);
        return `<div class="ceo-commitment-row">
          <span class="ceo-cmt-owner">${ROLE_SHORT[c.ownerRole] || c.ownerRole}</span>
          <span class="ceo-cmt-what">${escapeAttr(c.what)}</span>
          ${proj ? `<span class="ceo-cmt-proj">${escapeAttr(proj.clientName?.replace("（线索）", "") || c.projectId)}</span>` : ""}
        </div>`;
      }).join("")}
    </div>`;
}

function updateCeoDispatchStatus(meta) {
  const el = document.getElementById("ceo-dispatch-status");
  if (!el) return;
  const ds = meta?.dispatchSummary;
  if (!ds?.shouldDispatch && !meta?.workflowPending) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  const proj = ds?.projectId ? getProject(ds.projectId) : null;
  el.textContent = meta?.workflowPending
    ? `编排中${proj ? ` · ${proj.clientName?.replace("（线索）", "")}` : ""}…`
    : ds?.shouldDispatch
      ? `已派活${proj ? ` · ${proj.clientName?.replace("（线索）", "")}` : ""}`
      : "";
}

function onCeoFilesSelected() {
  const input = document.getElementById("ceo-files");
  const hint = document.getElementById("ceo-files-hint");
  if (!input || !hint) return;
  const names = [...(input.files || [])].map((f) => f.name);
  hint.textContent = names.length ? names.join("、") : "支持 .md / .pdf，可多选";
}

async function openCeoOffice() {
  try {
    await refreshDashboard();
  } catch (_) {
    /* keep cached data */
  }
  const ch = data.channels;
  const thread = renderCeoThreadHtml(data.ceoThread || []);

  openModal(`
    <div class="modal-hero" style="margin-bottom:0.75rem">
      <img src="../../assets/avatars/ceo.png" alt=""/>
      <div><h2>沈策 · CEO</h2><div class="sub">唯一管理接口 · 对话与指令</div></div>
    </div>
    <div class="channel-bar">
      <div class="channel-pill ${ch.feishu.connected ? "on" : ""}">${ch.feishu.label}<br><small>${ch.feishu.connected ? "已连接" : "—"}</small></div>
      <div class="channel-pill ${ch.wechat.connected ? "on" : ""}">${ch.wechat.label}<br><small>${ch.wechat.connected ? "已连接" : "—"}</small></div>
      <div class="channel-pill ${ch.web?.connected ? "on" : ""}">Web</div>
    </div>
    <p style="font-size:0.72rem;color:var(--text3);margin-bottom:0.75rem">随便聊；明确说让谁做什么，CEO 会理解并自动派活</p>
    ${renderOpenCommitmentsHtml()}
    <div id="ceo-dispatch-status" class="ceo-dispatch-status" hidden></div>
    <div class="thread">${thread}</div>
    <textarea class="brief-input" id="brief-input" placeholder="和 CEO 聊需求、讨论方案，或下达指令…" rows="3"></textarea>
    <div class="ceo-attach-row">
      <label class="icon-btn ceo-attach-icon" title="添加附件">
        <input type="file" id="ceo-files" accept=".md,.pdf,text/markdown,application/pdf" multiple hidden onchange="onCeoFilesSelected()"/>
        ${WR_ICONS.attach}
      </label>
      <span class="ceo-files-hint" id="ceo-files-hint">支持 .md / .pdf，可多选</span>
      ${iconBtn("send", "submitBrief()", "发送", "icon-btn-accent", "ceo-send-btn")}
    </div>
  `, "ceo-office");
  requestAnimationFrame(scrollCeoThreadToBottom);
  document.getElementById("brief-input")?.focus();
  document.getElementById("brief-input")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitBrief();
    }
  });
  updateCeoDispatchStatus(data?.meta || {});
}

async function submitBrief() {
  const input = document.getElementById("brief-input");
  const fileInput = document.getElementById("ceo-files");
  const text = input?.value?.trim() || "";
  const files = fileInput?.files ? [...fileInput.files] : [];
  if (!text && !files.length) return;
  const btn = document.getElementById("ceo-send-btn");
  if (btn) { btn.disabled = true; btn.classList.add("is-busy"); }
  const displayText = text || `（附件：${files.map((f) => f.name).join("、")}）`;
  input.value = "";
  if (fileInput) fileInput.value = "";
  onCeoFilesSelected();

  const now = new Date().toISOString();
  data.ceoThread = [
    ...data.ceoThread,
    { id: `local-${Date.now()}`, direction: "founder_to_ceo", channel: "web", text: displayText, at: now },
    { id: `local-ack-${Date.now()}`, direction: "ceo_to_founder", channel: "web", type: "ack", text: "…", at: now },
  ];
  updateCeoThreadPane();

  let processing = false;
  try {
    const res = await postCeoBrief(text, files);
    data.ceoThread = res.data.thread || data.ceoThread;
    updateCeoThreadPane(true);
    processing = !!(res.meta?.processing || res.meta?.workflowPending);
    updateCeoDispatchStatus({ ...res.meta, workflowPending: processing });
    if (processing) {
      await pollCeoThreadUntilSettled(true, 180000);
    }
  } catch (e) {
    alert(`发送失败：${e.message}`);
  } finally {
    if (btn) { btn.disabled = false; btn.classList.remove("is-busy"); }
    input?.focus();
    try {
      await refreshDashboard();
      renderAll();
      updateCeoThreadPane();
      refreshCeoCommitmentsPanel();
    } catch (_) {}
  }
}

function refreshCeoCommitmentsPanel() {
  if (!document.querySelector(".ceo-office")) return;
  const existing = document.querySelector(".ceo-office .ceo-commitments");
  const html = renderOpenCommitmentsHtml();
  if (existing) {
    if (html) existing.outerHTML = html;
    else existing.remove();
  } else if (html) {
    const anchor = document.getElementById("ceo-dispatch-status") || document.querySelector(".ceo-office .thread");
    anchor?.insertAdjacentHTML("beforebegin", html);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isCeoThreadPending(thread) {
  if (!thread?.length) return false;
  const last = thread[thread.length - 1];
  return last?.direction === "ceo_to_founder" && last?.type === "ack";
}

async function pollCeoThreadUntilSettled(workflowPending, maxMs = 180000, ctrl = null) {
  const start = Date.now();
  let stablePolls = 0;
  let lastSig = "";
  let wasPending = isCeoThreadPending(data.ceoThread || []);

  while (Date.now() - start < maxMs) {
    if (ctrl?.stop && !workflowPending) return;
    try {
      const json = await apiGet("/ceo/thread");
      data.ceoThread = json.data || data.ceoThread;
      const pending = isCeoThreadPending(data.ceoThread);
      if (wasPending && !pending) {
        updateCeoThreadPane(true);
        const last = [...(data.ceoThread || [])].reverse().find(
          (m) => m.direction === "ceo_to_founder" && m.type !== "ack"
        );
        if (last) await animateCeoReply(last);
      } else {
        updateCeoThreadPane(true);
      }
      wasPending = pending;
      await refreshDashboard();
      refreshCeoCommitmentsPanel();
      updateCeoDispatchStatus({
        workflowPending: pending || !!(data?.meta?.orchestrationActive),
        dispatchSummary: data?.meta?.lastCeoTurn || {},
      });
      renderOverview();
    } catch (_) {
      /* retry */
    }

    const thread = data.ceoThread || [];
    const last = thread[thread.length - 1];
    const pending = isCeoThreadPending(thread);
    const sig = `${thread.length}:${last?.id || ""}:${last?.type || ""}:${pending}:${last?.text?.length || 0}`;
    if (sig === lastSig && !pending) stablePolls += 1;
    else stablePolls = 0;
    lastSig = sig;

    if (!pending) {
      if (!workflowPending) return;
      const t = last?.text || "";
      if (
        last?.type === "decision"
        || t.includes("已派活")
        || t.includes("编排")
        || t.includes("Decision Memo")
        || t.includes("⚠️")
        || t.includes("已登记线索")
        || !(data?.meta?.orchestrationActive)
      ) {
        if (!data?.meta?.orchestrationActive) return;
      }
      if (stablePolls >= 3) return;
    }

    if (ctrl?.stop && !workflowPending) return;
    await sleep(800);
  }
}

/* ── Finance (Costs + Revenue) ── */
function renderProjectPnLBadge(pnl) {
  if (!pnl?.health) return "";
  const h = pnl.health;
  if (h === "healthy" || h === "strong") {
    return `<span class="project-tag pnl-${h}">毛利 ${fmtMoney(pnl.margin)} · ${pnl.marginPct}%</span>`;
  }
  if (h === "watch") {
    return `<span class="project-tag pnl-watch">未签约 · 已耗 ${fmtMoney(pnl.cost)}</span>`;
  }
  if (h === "pipeline") {
    return `<span class="project-tag pnl-pipeline">线索 · 成本 ${fmtMoney(pnl.cost || 0)}</span>`;
  }
  return `<span class="project-tag pnl-loss">亏损 ${fmtMoney(Math.abs(pnl.margin))}</span>`;
}

const API_PROVIDER_PRESETS = {
  OpenRouter: "https://openrouter.ai/api/v1",
  OpenAI: "https://api.openai.com/v1",
  Anthropic: "https://api.anthropic.com/v1",
  Moonshot: "https://api.moonshot.cn/v1",
  DeepSeek: "https://api.deepseek.com/v1",
  Ollama: "http://127.0.0.1:11434/v1",
  Custom: "",
};

async function loadSettingsView() {
  settingsRoleId = settingsRoleId || "ceo";
  try {
    roleConfigs = await loadRoleConfigs();
  } catch (e) {
    roleConfigs = data?.roleConfig || [];
  }
  try {
    runtimeSettings = (await apiGet("/runtime/settings")).data;
  } catch (e) {
    runtimeSettings = data?.meta?.runtimeSettings || null;
  }
  renderSettings();
}

function renderSettings() {
  const root = document.getElementById("settings-root");
  if (!root) return;

  const list = roleConfigs
    .map((cfg) => {
      const r = getRole(cfg.roleId);
      const hasKey = Boolean(cfg.apiKey?.masked);
      return `
        <button type="button" class="settings-role-btn ${cfg.roleId === settingsRoleId ? "active" : ""}"
          onclick="selectSettingsRole('${cfg.roleId}')">
          <img src="../../assets/avatars/${cfg.roleId}.png" alt=""/>
          <div>
            <div class="name">${r?.name || cfg.roleId}</div>
            <div class="meta">${cfg.model || "未设模型"} · ${cfg.apiProvider || "—"}</div>
          </div>
          <span class="settings-status ${hasKey ? "on" : "off"}">${hasKey ? "Key 已配" : "未配 Key"}</span>
        </button>`;
    })
    .join("");

  const cfg = roleConfigs.find((c) => c.roleId === settingsRoleId) || roleConfigs[0];
  if (cfg) settingsRoleId = cfg.roleId;
  const r = getRole(settingsRoleId);
  const cost = data?.costs?.byRole?.find((x) => x.roleId === settingsRoleId);
  const providers = Object.keys(API_PROVIDER_PRESETS)
    .map(
      (p) =>
        `<option value="${p}" ${cfg?.apiProvider === p ? "selected" : ""}>${p}</option>`
    )
    .join("");
  const keyHint = cfg?.apiKey?.masked ? `当前：${cfg.apiKey.masked}` : "尚未配置，保存后将加密存储";
  const rolePromptDoc = (cfg?.rolePrompt || "").trim();
  const fpDoc = (data?.founderProfile?.document || "").trim() || founderProfileDefaultDocument(data?.founderProfile);
  const pendingSuggestions = (data?.profileSuggestions || []).filter((s) => s.status === "pending").length;
  const rt = runtimeSettings || {};
  const pulse = rt.pulse || {};
  const agency = rt.agency || {};
  const auto = rt.ceoAutoDispatch || {};
  const founder = rt.founderNotify || {};

  root.innerHTML = `
    <div class="settings-live-banner glass-inner">
      <strong>实时后端已连接</strong> · 项目/收件箱等初始数据来自演示种子（可逐步被 Agent 更新）；
      Agent 调用、配置保存、CEO 简报走真实 LLM（已配 Key 的角色）。
    </div>
    <div class="settings-page">
      <aside class="settings-sidebar glass">
        <div class="settings-title">角色 API 配置</div>
        <div class="settings-sub">每个 Agent 可独立配置模型、Base URL 与 API Key。Key 仅存本地数据库，不会回显明文。</div>
        <div class="settings-role-list">${list}</div>
        <div class="settings-channel">
          <div class="modal-section-title">渠道</div>
          <div class="channel-bar" style="margin-top:0.5rem">
            <div class="channel-pill ${data.channels.feishu.connected ? "on" : ""}">${data.channels.feishu.label}</div>
            <div class="channel-pill ${data.channels.wechat.connected ? "on" : ""}">${data.channels.wechat.label}</div>
          </div>
        </div>
      </aside>
      <div class="settings-form-panel glass">
        <div class="settings-form-head">
          <img src="../../assets/avatars/${settingsRoleId}.png" alt=""/>
          <div>
            <h3>${r?.name || settingsRoleId} · ${ROLE_SHORT[settingsRoleId] || settingsRoleId}</h3>
            <p>${r?.title || ""} · 本月 Token 成本 ¥${cost?.cost || 0}</p>
          </div>
        </div>
        <div class="settings-fields">
          <div class="settings-field">
            <label for="set-provider">API 提供商</label>
            <select id="set-provider" onchange="onSettingsProviderChange()">${providers}</select>
          </div>
          <div class="settings-field">
            <label for="set-model">模型 ID</label>
            <input id="set-model" value="${escapeAttr(cfg?.model || "")}" placeholder="例如 gpt-4o / claude-sonnet-4 / deepseek-chat"/>
            <div class="hint">OpenRouter 填完整 slug，Ollama 填本地模型名</div>
          </div>
          <div class="settings-field">
            <label for="set-url">API Base URL</label>
            <input id="set-url" value="${escapeAttr(cfg?.apiBaseUrl || API_PROVIDER_PRESETS.OpenRouter)}" placeholder="https://..."/>
          </div>
          <div class="settings-field">
            <label for="set-key">API Key</label>
            <input id="set-key" type="password" autocomplete="off" placeholder="输入新 Key（留空则不修改）"/>
            <div class="hint">${keyHint}</div>
          </div>
          <div class="settings-field">
            <label for="set-budget">月预算（CNY）</label>
            <input id="set-budget" type="number" min="0" value="${cfg?.monthlyBudget || 0}"/>
          </div>
          <div class="settings-field">
            <label>工具白名单</label>
            <div class="settings-tools">${(cfg?.tools || []).map((t) => `<span class="chip">${t}</span>`).join("") || "—"}</div>
          </div>
          <div class="settings-field role-prompt-field">
            <div class="role-prompt-head">
              <label for="set-role-prompt">角色 System Prompt</label>
              <button type="button" class="btn-secondary btn-sm" id="role-prompt-preview-btn" onclick="toggleRolePromptPreview()">预览</button>
            </div>
            <p class="hint">定义 ${r?.name || settingsRoleId} 的职责边界、专业标准与输出要求 · 保存后该 Agent 每次 LLM 调用都会读取</p>
            <div class="founder-doc-shell role-prompt-shell">
              <textarea class="founder-doc-editor role-prompt-editor" id="set-role-prompt" spellcheck="false">${escapeAttr(rolePromptDoc)}</textarea>
              <div class="founder-doc-preview md-content" id="set-role-prompt-preview" hidden></div>
            </div>
          </div>
        </div>
        <div class="settings-actions">
          <button class="btn-primary" onclick="saveSettingsRole()">保存 ${r?.name || settingsRoleId} 配置</button>
          <button class="btn-secondary" onclick="testSettingsConnection()">测试连接</button>
        </div>
        <div class="settings-toast" id="settings-toast"></div>
      </div>
    </div>
    <div class="founder-profile-panel glass">
      <div class="founder-profile-head">
        <div>
          <h3>Founder Profile</h3>
          <p>以 Markdown 文档维护协作偏好 · CEO 各轮决策直接读取本文 · 收件箱采纳的建议会追加到「已确认偏好」</p>
        </div>
        <div class="founder-profile-actions">
          <button type="button" class="btn-secondary btn-sm" id="fp-preview-btn" onclick="toggleFounderProfilePreview()">预览</button>
          <button type="button" class="btn-primary btn-sm" onclick="saveFounderProfile()">保存文档</button>
        </div>
      </div>
      ${pendingSuggestions ? `<div class="founder-pending-hint">有 ${pendingSuggestions} 条 CEO 偏好建议待处理 · <button type="button" class="wf-link" onclick="goToView('inbox');setInboxFilter('profile_suggestion')">去收件箱</button></div>` : ""}
      <div class="founder-doc-shell glass-inner">
        <textarea class="founder-doc-editor" id="fp-document" spellcheck="false" placeholder="# Founder Profile">${escapeAttr(fpDoc)}</textarea>
        <div class="founder-doc-preview md-content" id="fp-document-preview" hidden></div>
      </div>
      <div class="founder-doc-foot">支持任意 Markdown：章节、列表、表格、链接。不必拘泥于固定字段。</div>
      <div class="settings-toast" id="founder-profile-toast"></div>
    </div>
    <div class="runtime-settings-panel glass">
      <div class="founder-profile-head">
        <div>
          <h3>编排运行时</h3>
          <p>Pulse 心跳与 Agency 自主观察的阈值 · 保存后立即生效，无需改代码</p>
        </div>
        <button type="button" class="btn-primary btn-sm" onclick="saveRuntimeSettings()">保存运行时配置</button>
      </div>
      <div class="settings-fields runtime-settings-grid">
        <div class="settings-field">
          <label><input type="checkbox" id="rt-pulse-enabled" ${pulse.enabled !== false ? "checked" : ""}/> 启用 Pulse 后台心跳</label>
          <p class="hint">关闭后任务仍可在 CEO 派活时同步执行；重启后 pending 队列需手动 drain 或重新开启</p>
        </div>
        <div class="settings-field">
          <label><input type="checkbox" id="rt-agency-enabled" ${agency.enabled !== false ? "checked" : ""}/> 启用 Agency 自主观察</label>
          <p class="hint">各角色按规则扫描任务/项目缺口，向 CEO 收件箱写入建议（0 Token）</p>
        </div>
        <div class="settings-field">
          <label for="rt-exec-interval">任务执行间隔（秒，有 pending 时）</label>
          <input id="rt-exec-interval" type="number" min="2" max="120" value="${pulse.executionIntervalSec ?? 5}"/>
        </div>
        <div class="settings-field">
          <label for="rt-stale-min">Running 超时重置（分钟）</label>
          <input id="rt-stale-min" type="number" min="5" max="240" value="${pulse.runningStaleMin ?? 30}"/>
        </div>
        <div class="settings-field">
          <label for="rt-ceo-observe">CEO 全局观察间隔（秒）</label>
          <input id="rt-ceo-observe" type="number" min="60" max="3600" value="${agency.ceoObserveIntervalSec ?? 300}"/>
          <p class="hint">Phase B 启用 Agency 后生效</p>
        </div>
        <div class="settings-field">
          <label><input type="checkbox" id="rt-auto-dispatch" ${auto.enabled ? "checked" : ""}/> <strong>CEO 自动派活</strong></label>
          <p class="hint">开启后，对低危 proposal 在满足交付分 / 冷却条件时自动 dispatch（可在收件箱看到「已自动派活」）</p>
        </div>
        <div class="settings-field">
          <label><input type="checkbox" id="rt-ceo-deliberate-llm" ${agency.ceoDeliberateUseLlm ? "checked" : ""}/> CEO Deliberate 使用 LLM 注释</label>
          <p class="hint">关闭时仅规则合并同类建议；开启后 CEO 已配 Key 时会对建议加一句评估（optional）</p>
        </div>
        <div class="settings-field">
          <label for="rt-auto-score">自动派活 · 最低交付分</label>
          <input id="rt-auto-score" type="number" min="0" max="100" value="${auto.minDeliveryScore ?? 80}"/>
        </div>
        <div class="settings-field">
          <label for="rt-auto-risk">自动派活 · 最高风险级别</label>
          <select id="rt-auto-risk">
            <option value="low" ${auto.maxRiskLevel === "low" ? "selected" : ""}>low · 仅流程推进类</option>
            <option value="medium" ${auto.maxRiskLevel === "medium" ? "selected" : ""}>medium · 含一般业务建议</option>
          </select>
        </div>
        <div class="settings-field">
          <label for="rt-auto-cooldown">自动派活 · 同项目冷却（分钟）</label>
          <input id="rt-auto-cooldown" type="number" min="5" max="1440" value="${auto.cooldownMin ?? 15}"/>
        </div>
        <div class="settings-field">
          <label for="rt-founder-cooldown">Founder 问询冷却（小时）</label>
          <input id="rt-founder-cooldown" type="number" min="1" max="168" value="${founder.openQuestionCooldownHours ?? 24}"/>
        </div>
      </div>
      <div class="settings-toast" id="runtime-settings-toast"></div>
    </div>`;
}

function founderProfileDefaultDocument(fp) {
  const comm = fp?.communication || {};
  const legal = (fp?.deliverables || {})?.legal || {};
  const hitl = (fp?.escalation || {})?.alwaysHitlFor || ["contract", "sow"];
  const delivery = [
    legal.preferMutualNdaTemplate ? "- 法务 NDA 默认用双向专业模板" : null,
    legal.rejectBulletDraft ? "- 不要 bullet 草稿式法务文档" : null,
    "- （在此补充交付标准）",
  ].filter(Boolean);
  return [
    "# Founder Profile",
    "",
    "CEO 与你的协作约定。用 Markdown 自由书写，保存后各轮 CEO 决策会读取本文档。",
    "",
    "## 沟通",
    comm.preferConcise ? "- 回复简洁，先结论" : "- （在此补充沟通偏好）",
    `- CEO 单条回复不超过 ${comm.maxReplySentences || 8} 句`,
    "",
    "## 交付物偏好",
    ...delivery,
    "",
    "## 升级与审批",
    `- 以下类型必须经你 HITL 批准：${hitl.join(", ")}`,
    "",
    "## 已确认偏好",
    "- （CEO 从对话中建议、经你采纳的内容会追加在此）",
  ].join("\n");
}

let founderProfilePreviewOn = false;
let rolePromptPreviewOn = false;

function toggleRolePromptPreview() {
  rolePromptPreviewOn = !rolePromptPreviewOn;
  const editor = document.getElementById("set-role-prompt");
  const preview = document.getElementById("set-role-prompt-preview");
  const btn = document.getElementById("role-prompt-preview-btn");
  if (!editor || !preview) return;
  if (rolePromptPreviewOn) {
    preview.innerHTML = simpleMarkdown(editor.value || "");
    preview.hidden = false;
    editor.hidden = true;
    if (btn) btn.textContent = "编辑";
  } else {
    preview.hidden = true;
    editor.hidden = false;
    if (btn) btn.textContent = "预览";
  }
}

function toggleFounderProfilePreview() {
  founderProfilePreviewOn = !founderProfilePreviewOn;
  const editor = document.getElementById("fp-document");
  const preview = document.getElementById("fp-document-preview");
  const btn = document.getElementById("fp-preview-btn");
  if (!editor || !preview) return;
  if (founderProfilePreviewOn) {
    preview.innerHTML = simpleMarkdown(editor.value || "");
    preview.hidden = false;
    editor.hidden = true;
    if (btn) btn.textContent = "编辑";
  } else {
    preview.hidden = true;
    editor.hidden = false;
    if (btn) btn.textContent = "预览";
  }
}

function escapeAttr(s) {
  return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function selectSettingsRole(roleId) {
  settingsRoleId = roleId;
  rolePromptPreviewOn = false;
  founderProfilePreviewOn = false;
  renderSettings();
}

function onSettingsProviderChange() {
  const provider = document.getElementById("set-provider")?.value;
  const urlInput = document.getElementById("set-url");
  if (!urlInput || !provider || provider === "Custom") return;
  const preset = API_PROVIDER_PRESETS[provider];
  if (preset) urlInput.value = preset;
}

async function saveFounderProfile() {
  const toast = document.getElementById("founder-profile-toast");
  const documentText = document.getElementById("fp-document")?.value ?? "";
  if (!documentText.trim()) {
    if (toast) toast.textContent = "文档不能为空";
    return;
  }
  try {
    const res = await apiPut("/founder/profile", { document: documentText });
    data.founderProfile = res.data;
    founderProfilePreviewOn = false;
    if (toast) toast.textContent = "✓ Founder Profile 文档已保存";
    renderSettings();
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function saveRuntimeSettings() {
  const toast = document.getElementById("runtime-settings-toast");
  const body = {
    pulse: {
      enabled: document.getElementById("rt-pulse-enabled")?.checked ?? true,
      executionIntervalSec: Number(document.getElementById("rt-exec-interval")?.value || 5),
      runningStaleMin: Number(document.getElementById("rt-stale-min")?.value || 30),
    },
    agency: {
      enabled: document.getElementById("rt-agency-enabled")?.checked ?? true,
      ceoObserveIntervalSec: Number(document.getElementById("rt-ceo-observe")?.value || 300),
      ceoDeliberateUseLlm: document.getElementById("rt-ceo-deliberate-llm")?.checked ?? false,
    },
    ceoAutoDispatch: {
      enabled: document.getElementById("rt-auto-dispatch")?.checked ?? false,
      minDeliveryScore: Number(document.getElementById("rt-auto-score")?.value || 80),
      maxRiskLevel: document.getElementById("rt-auto-risk")?.value || "low",
      cooldownMin: Number(document.getElementById("rt-auto-cooldown")?.value || 15),
    },
    founderNotify: {
      openQuestionCooldownHours: Number(document.getElementById("rt-founder-cooldown")?.value || 24),
    },
  };
  try {
    const res = await apiPatch("/runtime/settings", body);
    runtimeSettings = res.data;
    if (toast) toast.textContent = "✓ 运行时配置已保存";
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function saveSettingsRole() {
  const toast = document.getElementById("settings-toast");
  const body = {
    model: document.getElementById("set-model")?.value?.trim(),
    apiProvider: document.getElementById("set-provider")?.value,
    apiBaseUrl: document.getElementById("set-url")?.value?.trim(),
    monthlyBudget: Number(document.getElementById("set-budget")?.value || 0),
    rolePrompt: document.getElementById("set-role-prompt")?.value ?? "",
  };
  const key = document.getElementById("set-key")?.value?.trim();
  if (key) body.apiKey = key;
  try {
    const res = await apiPut(`/roles/config/${settingsRoleId}`, body);
    const idx = roleConfigs.findIndex((c) => c.roleId === settingsRoleId);
    if (idx >= 0) roleConfigs[idx] = res.data;
    await refreshDashboard();
    if (toast) toast.textContent = "✓ 已保存并加密存储";
    document.getElementById("set-key").value = "";
    renderSettings();
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function testSettingsConnection() {
  const toast = document.getElementById("settings-toast");
  if (toast) toast.textContent = "正在保存并测试连接…";
  try {
    await saveSettingsRole();
    const body = {
      model: document.getElementById("set-model")?.value?.trim(),
      apiProvider: document.getElementById("set-provider")?.value,
      apiBaseUrl: document.getElementById("set-url")?.value?.trim(),
    };
    const key = document.getElementById("set-key")?.value?.trim();
    if (key) body.apiKey = key;
    const res = await apiPost(`/roles/config/${settingsRoleId}/test`, body);
    if (toast) {
      toast.textContent = `✓ 连接成功 · ${res.data.model} @ ${res.data.baseUrl || ""} · ${(res.data.sample || "").slice(0, 60)}`;
    }
  } catch (e) {
    if (toast) toast.textContent = `✗ ${e.message}`;
  }
}

function showRoleConfig(roleId) {
  settingsRoleId = roleId;
  goToView("settings");
}

async function saveRoleConfig(roleId) {
  settingsRoleId = roleId;
  await saveSettingsRole();
}

window.selectSettingsRole = selectSettingsRole;
window.onSettingsProviderChange = onSettingsProviderChange;
window.saveSettingsRole = saveSettingsRole;
window.saveRuntimeSettings = saveRuntimeSettings;
window.testSettingsConnection = testSettingsConnection;

window.showRoleModalStacked = showRoleModalStacked;
window.showRoleModal = showRoleModal;
window.showStatsModal = showStatsModal;
window.showClientDetail = showClientDetail;
window.openWorkroom = openWorkroom;
window.selectArtifact = selectArtifact;
window.setInboxFilter = setInboxFilter;
window.setInboxStatusFilter = setInboxStatusFilter;
window.openInboxItem = openInboxItem;
window.approveHitl = approveHitl;
window.rejectHitl = rejectHitl;
window.resolveRequest = resolveRequest;
window.resolveProposal = resolveProposal;
window.adoptProfileSuggestion = adoptProfileSuggestion;
window.dismissProfileSuggestion = dismissProfileSuggestion;
window.onCeoFilesSelected = onCeoFilesSelected;
window.saveFounderProfile = saveFounderProfile;
window.toggleRolePromptPreview = toggleRolePromptPreview;
window.toggleFounderProfilePreview = toggleFounderProfilePreview;
window.closeModal = closeModal;
window.markClosureItem = markClosureItem;
window.exportCurrentMd = exportCurrentMd;
window.exportCurrentPdf = exportCurrentPdf;
window.exportProjectZip = exportProjectZip;
window.exportClientDeliveryZip = exportClientDeliveryZip;
window.openArtifactEditor = openArtifactEditor;
window.cancelArtifactEditor = cancelArtifactEditor;
window.saveArtifactContent = saveArtifactContent;
window.submitArtifactForReview = submitArtifactForReview;
window.toggleArtifactDiff = toggleArtifactDiff;
window.goToWeekly = goToWeekly;
window.showRoleConfig = showRoleConfig;
window.saveRoleConfig = saveRoleConfig;

init().catch(() => {
  document.body.innerHTML = '<div style="padding:2rem;text-align:center;font-family:-apple-system,sans-serif"><p>无法连接后端，请在项目根目录运行</p><code>./start.sh</code></div>';
});
