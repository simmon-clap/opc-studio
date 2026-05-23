/** Workroom v2 — grouped nav, focus bar, action-driven toolbar */

const ART_GROUP_ORDER = ["evaluate", "legal", "engineering", "delivery", "ops"];
const ART_GROUP_LABELS = {
  evaluate: "阶段2 · 评估立项",
  legal: "阶段3 · 方案签约",
  engineering: "阶段4 · 开发交付",
  delivery: "阶段5 · 验收结项",
  ops: "运营台账",
};
const ART_KIND_LABELS = {
  memo: "评估备忘", prd: "PRD", nda: "NDA", contract: "合同", sow: "SOW",
  quote: "报价", tech_spec: "技术方案", code: "代码", demo: "Demo",
  design: "设计稿", acceptance: "验收", closure: "结项", email: "邮件",
  ops_record: "台账", doc: "文档",
};
const ART_STATUS_LABELS = {
  draft: "草稿",
  revision: "CEO 修订中",
  review: "待评审",
  approved: "已定稿",
};

let workroomSelectedFile = null;
let workroomDiffMode = false;
let workroomDiffFrom = null;
let workroomDiffLines = null;
let workroomDiffTo = null;
let workroomEditMode = false;
let workroomEditContent = null;
let workroomData = null;
let briefEditOpen = false;
let openDropdownId = null;
let suppressDropdownClose = false;
let workroomViewVersion = null;

function isWorkroomUiInteractive() {
  if (openDropdownId || suppressDropdownClose) return true;
  if (briefEditOpen || workroomEditMode) return true;
  if (document.getElementById("sheet-backdrop")?.hidden) return false;
  const ae = document.activeElement;
  if (ae?.closest("#workroom-sheet")) {
    const tag = ae.tagName;
    if (tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT") return true;
  }
  return false;
}

function captureWorkroomUiState() {
  return {
    dropdownId: openDropdownId || document.querySelector(".wr-dropdown.open")?.id || null,
    folds: [...document.querySelectorAll("#workroom-nav details[data-fold-key]")]
      .filter((d) => d.open)
      .map((d) => d.dataset.foldKey),
    focusOthers: !!document.querySelector(".focus-others[open]"),
    viewVersion: workroomViewVersion,
  };
}

function restoreWorkroomUiState(ui) {
  if (!ui) return;
  (ui.folds || []).forEach((key) => {
    document.querySelector(`#workroom-nav details[data-fold-key="${CSS.escape(key)}"]`)?.setAttribute("open", "");
  });
  if (ui.focusOthers) document.querySelector(".focus-others")?.setAttribute("open", "");
  if (ui.dropdownId) {
    openDropdownId = ui.dropdownId;
    document.getElementById(ui.dropdownId)?.classList.add("open");
  }
  if (ui.viewVersion) workroomViewVersion = ui.viewVersion;
}

function artifactCanInlineEdit(art) {
  return (art?.actions || []).some((a) => a.id === "edit");
}

function onArtifactContentClick(e) {
  if (e.target.closest("a, button, input, textarea, select, .icon-btn, .wr-dropdown")) return;
  const art = getEnrichedArtifact(workroomArtifactId);
  if (!artifactCanInlineEdit(art)) return;
  openArtifactEditor();
}

function onBriefBodyClick(e) {
  if (briefEditOpen) return;
  if (e.target.closest("button, textarea, input, .icon-btn")) return;
  toggleBriefEditor();
}

function renderRoleAvatarsNav(roleIds, max = 4) {
  const ids = [...new Set((roleIds || []).filter(Boolean))];
  if (!ids.length || typeof assigneeAvatarsInteractive !== "function") return "";
  return assigneeAvatarsInteractive(ids, max, 22);
}

function renderPriorityPicker(priority) {
  const p = priority || "P2";
  const opts = ["P0", "P1", "P2", "P3"]
    .map((x) => `<button type="button" onclick="event.stopPropagation();setProjectPriority('${x}')">${x}</button>`)
    .join("");
  return `
    <div class="wr-dropdown" id="priority-dd">
      <button type="button" class="priority pri-${p} sheet-priority wr-priority-btn" onclick="toggleDropdown('priority-dd', event)" title="调整优先级">
        <span>${p}</span>${WR_ICONS.chevronDown}
      </button>
      <div class="wr-dropdown-menu" onclick="event.stopPropagation()">${opts}</div>
    </div>`;
}

async function setProjectPriority(priority) {
  closeAllDropdowns();
  if (!workroomProjectId) return;
  const current = getProject(workroomProjectId)?.priority;
  if (priority === current) return;
  try {
    const res = await apiPatch(`/projects/${workroomProjectId}`, { priority });
    const updated = res.data?.project;
    const p = getProject(workroomProjectId);
    if (p && updated) Object.assign(p, updated);
    await refreshDashboard();
    renderProjects();
    updateBadges();
    if (getActiveViewId() === "inbox") renderInbox();
    await renderWorkroomShell(workroomProjectId, workroomArtifactId);
    if (res.data?.priorityChanged) {
      showWorkroomToast(`优先级 ${current || "—"} → ${priority} · 已通知 CEO 调整任务排期`);
    }
  } catch (e) {
    const stale = /405|404|Method Not Allowed|Not Found/i.test(String(e.message));
    const hint = stale ? "\n\n后端可能未重启：终端 Ctrl+C 停旧进程，再运行 ./start.sh" : "";
    alert(`优先级更新失败：${e.message}${hint}`);
  }
}

async function saveBriefFromEditor() {
  const qsEl = document.getElementById("brief-open-questions");
  const scopeEl = document.getElementById("brief-scope");
  if (!qsEl || !workroomProjectId) return;
  const openQuestions = qsEl.value.split("\n").map((s) => s.trim()).filter(Boolean);
  const scope = scopeEl?.value?.trim() || undefined;
  try {
    await apiPatch(`/projects/${workroomProjectId}/brief`, { openQuestions, scope });
    briefEditOpen = false;
    await refreshDashboard();
    await renderWorkroomShell(workroomProjectId, workroomArtifactId);
  } catch (e) {
    alert(`Brief 保存失败：${e.message}`);
  }
}

function toggleBriefEditor() {
  briefEditOpen = !briefEditOpen;
  document.getElementById("workroom-nav").innerHTML = renderWorkroomNavGrouped(
    workroomProjectId,
    workroomArtifactId,
    workroomData
  );
}

const STATUS_DOT = { waiting: "⏳", done: "●", revision: "↻", active: "○", placeholder: "—" };
const FOCUS_TYPE_LABEL = {
  hitl: "待批", fill: "待填", running: "执行中", pending: "队列",
  question: "待确认", commitment: "承诺", process: "流程",
};

function closeAllDropdowns() {
  openDropdownId = null;
  document.querySelectorAll(".wr-dropdown.open").forEach((el) => el.classList.remove("open"));
}

function toggleDropdown(id, ev) {
  if (ev) {
    ev.preventDefault();
    ev.stopPropagation();
  }
  const el = document.getElementById(id);
  if (!el) return;
  const willOpen = openDropdownId !== id;
  closeAllDropdowns();
  if (willOpen) {
    openDropdownId = id;
    suppressDropdownClose = true;
    el.classList.add("open");
    requestAnimationFrame(() => {
      requestAnimationFrame(() => { suppressDropdownClose = false; });
    });
  }
}

document.addEventListener("mousedown", (e) => {
  if (e.target.closest(".wr-dropdown")) {
    suppressDropdownClose = true;
    setTimeout(() => { suppressDropdownClose = false; }, 120);
  }
});

document.addEventListener("click", (e) => {
  if (suppressDropdownClose || e.target.closest(".wr-dropdown")) return;
  closeAllDropdowns();
});

function showWorkroomToast(msg) {
  let el = document.getElementById("workroom-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "workroom-toast";
    el.className = "workroom-toast";
    document.getElementById("workroom-sheet")?.appendChild(el);
  }
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.hidden = true; }, 2800);
}

async function loadWorkroomData(projectId) {
  try {
    const res = await apiGet(`/projects/${projectId}/workroom`);
    workroomData = res.data;
  } catch (e) {
    workroomData = null;
    if (/405|404|Method Not Allowed|Not Found/i.test(String(e.message))) {
      showWorkroomToast("工作室 API 不可用 · 请重启后端 ./start.sh");
    }
  }
  return workroomData;
}

function renderWorkroomHeader(header) {
  const stageEl = document.getElementById("sheet-stage-line");
  if (!stageEl || !header) return;
  const pd = header.progressDetail || {};
  const hitl = header.hitlPending
    ? `<span class="sheet-hitl-dot">${escapeHtml(header.hitlPending)} 待批</span>`
    : "";
  const exec = pd.executionProgress != null
    ? `<span class="sheet-exec">执行 ${pd.executionProgress}%</span>`
    : "";
  stageEl.innerHTML = `
    ${renderPriorityPicker(header.priority)}
    <span class="sheet-stage">${escapeHtml(header.stageShort || header.stage || "")}</span>
    <span class="sheet-pct" title="阶段进度">${header.progress || 0}%</span>
    ${exec}
    ${hitl}`;
  renderWorkroomProjectBar(header);
  renderProjectExportMenu(header.exportMenu || workroomData?.exportMenu || []);
}

function renderWorkroomProjectBar(header) {
  const bar = document.getElementById("sheet-project-bar");
  if (!bar) return;
  const tags = [
    header.hitlPending ? `<span class="project-tag tag-hitl">${escapeHtml(header.hitlPending)} 待批</span>` : "",
    header.closureTag ? `<span class="project-tag tag-closure">${escapeHtml(header.closureTag)}</span>` : "",
    header.pnlHealth ? `<span class="project-tag tag-pnl-${header.pnlHealth}">${header.pnlHealth === "healthy" ? "盈利" : header.pnlHealth === "watch" ? "需关注" : "线索"}</span>` : "",
  ].filter(Boolean);
  const assignees = assigneeAvatarsInteractive(header.assignees || [], 5, 24);
  const execNote = header.progressDetail?.executionNote;
  bar.hidden = !(header.summary || tags.length || assignees || execNote);
  bar.innerHTML = `
    <div class="sheet-project-main">
      ${header.summary ? `<details class="sheet-summary"><summary>${escapeHtml(header.summary.slice(0, 48))}${header.summary.length > 48 ? "…" : ""}</summary><p>${escapeHtml(header.summary)}</p>${header.agentDeliverable ? `<p class="sheet-deliverable">${escapeHtml(header.agentDeliverable)}</p>` : ""}</details>` : ""}
      ${execNote ? `<div class="sheet-exec-note">${escapeHtml(execNote)}</div>` : ""}
    </div>
    <div class="sheet-project-side">
      <div class="sheet-project-tags">${tags.join("") || ""}</div>
      <div class="sheet-project-roles">${assignees}</div>
    </div>`;
}

function renderProjectExportMenu(menu) {
  const wrap = document.getElementById("project-export-wrap");
  if (!wrap) return;
  if (!menu.length) { wrap.innerHTML = ""; return; }
  const items = menu.map((m) =>
    `<button type="button" onclick="projectExport('${m.id}')">${escapeHtml(m.label)}</button>`
  ).join("");
  wrap.innerHTML = iconDropdown("project-export-dd", "download", "导出项目", items);
}

async function projectExport(kind) {
  closeAllDropdowns();
  if (kind === "client") await exportClientDeliveryZip();
  else await exportProjectZip();
}

function renderWorkroomFocus(data) {
  const el = document.getElementById("workroom-focus");
  if (!el) return;
  const focus = data?.focus;
  const others = data?.others || [];
  if (!focus && !others.length) { el.hidden = true; return; }
  el.hidden = false;
  const renderStep = (s, highlight) => {
    const click = s.artifactId
      ? `onclick="selectArtifact('${s.artifactId}')"`
      : s.hitlId && s.artifactId
        ? `onclick="selectArtifact('${s.artifactId}')"`
        : "";
    const tag = FOCUS_TYPE_LABEL[s.type] || s.type || "提示";
    return `
      <button type="button" class="focus-step ${highlight ? "focus-primary" : "focus-secondary"}" ${click}>
        <span class="focus-tag">${tag}</span>
        <span class="focus-msg">${escapeHtml(s.message || "")}</span>
      </button>`;
  };
  el.innerHTML = `
    ${focus ? renderStep(focus, true) : ""}
    ${others.length ? `
      <details class="focus-others">
        <summary>还有 ${others.length} 项</summary>
        <div class="focus-others-list">${others.map((s) => renderStep(s, false)).join("")}</div>
      </details>` : ""}`;
}

function renderNavFold(fold) {
  const foldRoles = renderRoleAvatarsNav(fold.roles);
  const foldKey = `${fold.type}-${(fold.label || "").replace(/"/g, "")}`;
  if (fold.type === "brief") {
    const brief = fold.brief || {};
    const qs = (fold.openQuestions || []).map((q) => `<li>${escapeHtml(q)}</li>`).join("");
    const facts = (brief.confirmedFacts || []).map((f) => `<li>${escapeHtml(f)}</li>`).join("");
    const viewBody = `
      ${brief.scope ? `<p class="brief-scope-line">${escapeHtml(brief.scope)}</p>` : ""}
      ${facts ? `<ul class="brief-facts-compact">${facts}</ul>` : ""}
      ${qs ? `<ul class="brief-questions-compact">${qs}</ul>` : ""}
      ${!(brief.scope || facts || qs) ? `<p class="brief-empty-hint">点击编辑 Brief</p>` : ""}`;
    const editor = `
      <div class="founder-doc-shell glass-inner brief-doc-shell">
        <label class="brief-editor-label">待确认（每行一项）</label>
        <textarea id="brief-open-questions" class="founder-doc-editor brief-doc-editor" rows="4">${(fold.openQuestions || []).map(escapeHtml).join("\n")}</textarea>
        <label class="brief-editor-label">范围</label>
        <input id="brief-scope" class="brief-editor-input" value="${escapeHtml(brief.scope || "")}" placeholder="项目范围"/>
      </div>`;
    return `
      <details class="nav-fold nav-fold-brief" open data-fold-key="${escapeAttr(foldKey)}">
        <summary class="nav-fold-summary">
          <span class="nav-fold-dot">⏳</span>
          <span class="nav-fold-label">${escapeHtml(fold.label)}</span>
          ${foldRoles}
          ${briefEditOpen ? microBtn("check", "saveBriefFromEditor()", "保存 Brief", "micro-accent") : ""}
          ${briefEditOpen ? microBtn("x", "toggleBriefEditor()", "取消") : ""}
        </summary>
        <div class="nav-fold-body ${briefEditOpen ? "" : "brief-clickable"}" ${briefEditOpen ? "" : 'onclick="onBriefBodyClick(event)"'}>${briefEditOpen ? editor : viewBody}</div>
      </details>`;
  }
  if (fold.type === "deliberation") {
    const d = fold.data || {};
    const turns = (d.turns || []).map((t) => `
      <div class="delib-turn compact">
        <span class="delib-author">${ROLE_SHORT?.[t.author] || t.author}</span>
        <p>${escapeHtml(t.content || "")}</p>
      </div>`).join("");
    return `
      <details class="nav-fold" data-fold-key="${escapeAttr(foldKey)}">
        <summary class="nav-fold-summary">
          <span class="nav-fold-dot">●</span>
          <span class="nav-fold-label">${escapeHtml(fold.label)}</span>
          ${foldRoles}
        </summary>
        <div class="nav-fold-body">
          <div class="delib-agenda compact">${(d.agenda || []).map((a) => `<span class="chip">${escapeHtml(a)}</span>`).join("")}</div>
          <div class="delib-turns">${turns}</div>
        </div>
      </details>`;
  }
  if (fold.type === "closure") {
    const cl = fold.data || {};
    const items = (cl.checklist || []).map((item) => {
      const avatars = renderRoleAvatarsNav([item.roleId], 1);
      return `
        <div class="closure-item compact ${item.done ? "done" : ""}">
          <span class="closure-check">${item.done ? "☑" : "☐"}</span>
          <span class="closure-label">${escapeHtml(item.label || "")}</span>
          ${avatars}
        </div>`;
    }).join("");
    return `
      <details class="nav-fold" data-fold-key="${escapeAttr(foldKey)}">
        <summary class="nav-fold-summary">
          <span class="nav-fold-dot">${cl.status === "closed" ? "●" : "⏳"}</span>
          <span class="nav-fold-label">${escapeHtml(fold.label)}</span>
          ${foldRoles}
        </summary>
        <div class="nav-fold-body">
          ${cl.status === "in_closure" ? iconBtn("download", "exportClientDeliveryZip()", "导出客户 ZIP", "icon-btn-sm") : ""}
          <div class="closure-list compact">${items}</div>
        </div>
      </details>`;
  }
  return "";
}

function artifactKind(art) {
  return art.kind || art.type || "doc";
}

function artifactViewer(art) {
  if (art.viewer) return art.viewer;
  if (art.format === "code" || art.files?.length) return "code";
  if (art.format === "image" || art.images?.length) return "gallery";
  const map = {
    nda: "contract", contract: "contract", sow: "contract",
    prd: "prd", tech_spec: "prd", acceptance: "checklist", closure: "checklist",
    email: "email", memo: "memo", code: "code", demo: "demo", design: "gallery",
  };
  return map[artifactKind(art)] || "markdown";
}

function artifactGroup(art) {
  return art.group || ({
    memo: "evaluate", prd: "legal",
    nda: "legal", contract: "legal", sow: "legal", quote: "legal",
    tech_spec: "engineering", code: "engineering", demo: "engineering", design: "engineering",
    acceptance: "delivery", closure: "delivery", email: "engineering",
    ops_record: "ops", doc: "ops",
  }[artifactKind(art)] || "ops");
}

function highlightPendingFields(html) {
  return html.replace(
    /\[待填写[：:][^\]]*\]|\[待填写\]/g,
    (m) => `<mark class="art-pending">${m}</mark>`
  );
}

function extractMdSections(md) {
  const lines = (md || "").split("\n");
  const sections = [];
  lines.forEach((line, idx) => {
    const m = line.match(/^(#{1,3})\s+(.+)/);
    if (m) sections.push({ level: m[1].length, title: m[2], line: idx });
  });
  return sections;
}

function renderArtifactQualityBar(art) {
  const q = art.quality || {};
  const status = ART_STATUS_LABELS[art.status] || art.status || "草稿";
  const score = q.score != null ? `${q.score}/100` : (art.ceoReviewScore != null ? `${art.ceoReviewScore}/100` : "—");
  const pending = art.pendingFields || q.pendingFields || 0;
  const issues = (q.issues || []).slice(0, 2).join(" · ");
  const reviewNotes = art.reviewNotes || [];
  const latestNote = reviewNotes[0];
  return `
    <div class="art-quality-bar">
      <span class="art-status art-status-${art.status || "draft"}">${status}</span>
      <span class="art-quality-score">质量 ${score}</span>
      ${pending ? `<span class="art-pending-count">${pending} 处待填写</span>` : ""}
      ${issues ? `<span class="art-quality-issues">${issues}</span>` : ""}
      ${art.templateId ? `<span class="art-template">模板 ${art.templateId}</span>` : ""}
    </div>
    ${latestNote?.note ? `
    <div class="art-review-notes">
      <div class="art-review-notes-head">CEO 修订意见 · 第 ${latestNote.round || reviewNotes.length} 轮</div>
      <p>${escapeHtml(latestNote.note)}</p>
      ${reviewNotes.length > 1 ? `<details><summary>查看 ${reviewNotes.length - 1} 条历史意见</summary>${reviewNotes.slice(1).map((n) => `<p class="art-review-note-old">第 ${n.round || "?"} 轮：${escapeHtml(n.note || "")}</p>`).join("")}</details>` : ""}
    </div>` : ""}`;
}

function escapeHtml(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeAttr(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function renderArtifactActionBar(art) {
  if (workroomDiffMode || workroomEditMode) return "";
  const actions = (art.actions || []).filter((a) => a.id !== "edit");
  const pending = art.pendingFields || art.quality?.pendingFields || 0;
  if (!actions.length && !pending) return "";
  return `
    <div class="art-action-bar">
      ${pending ? `<span class="art-action-hint">${pending} 处待填写</span>` : ""}
      <div class="art-action-buttons">
        ${actions.map((a) => {
          const icon = ACTION_ICON[a.id] || "more";
          const title = ACTION_TITLE[a.id] || a.label;
          const accent = a.primary ? " icon-btn-accent" : "";
          return iconBtn(icon, `handleArtifactAction('${a.id}','${art.id}','${art.hitlId || ""}')`, title, accent);
        }).join("")}
      </div>
    </div>`;
}

function handleArtifactAction(actionId, artifactId, hitlId) {
  if (actionId === "edit") openArtifactEditor();
  else if (actionId === "submit_review") submitArtifactForReview();
  else if (actionId === "approve") approveArtifact(artifactId);
  else if (actionId === "reject") rejectArtifactHitl(artifactId, hitlId);
}

function renderArtifactExportMenu(art) {
  const formats = art.exportFormats || [{ id: "md", label: "Markdown" }, { id: "pdf", label: "PDF" }];
  const items = formats.map((f) =>
    `<button type="button" onclick="artifactExport('${f.id}')">${escapeHtml(f.label)}</button>`
  ).join("");
  return iconDropdown("art-export-dd", "download", "导出交付", items);
}

async function artifactExport(format) {
  closeAllDropdowns();
  const art = getArtifact(workroomArtifactId);
  if (!art) return;
  if (format === "md") exportCurrentMd();
  else if (format === "pdf") exportCurrentPdf();
  else if (format === "zip") await exportArtifactZip(art);
  else if (format === "link") {
    const url = art.demoUrl || (art.content || "").match(/https?:\/\/[^\s`)]+/)?.[0];
    if (url) {
      try { await navigator.clipboard.writeText(url); alert("链接已复制"); }
      catch (_) { prompt("复制链接", url); }
    }
  }
}

async function exportArtifactZip(art) {
  if (!window.JSZip || !(art.files || []).length) return;
  const zip = new JSZip();
  (art.files || []).forEach((f) => zip.file(f.path, f.content || ""));
  if (art.content) zip.file(`${slugify(art.title || "doc")}.md`, art.content);
  const blob = await zip.generateAsync({ type: "blob" });
  const p = getProject(workroomProjectId);
  downloadBlob(blob, `${slugify(p?.clientName)}_${slugify(art.title)}.zip`, "application/zip");
}

function openArtifactEditor() {
  const art = getArtifact(workroomArtifactId);
  if (!art) return;
  workroomEditMode = true;
  workroomDiffMode = false;
  workroomDiffLines = null;
  workroomEditContent = art._viewContent || art.content || "";
  renderWorkroomArtifactContent();
}

function cancelArtifactEditor() {
  workroomEditMode = false;
  workroomEditContent = null;
  renderWorkroomArtifactContent();
}

async function saveArtifactContent() {
  const textarea = document.getElementById("art-editor-content");
  if (!textarea) return;
  const content = textarea.value;
  try {
    await apiPut(`/projects/${workroomProjectId}/artifacts/${workroomArtifactId}/content`, {
      content,
      note: "Founder 填写",
    });
    workroomEditMode = false;
    workroomEditContent = null;
    await refreshDashboard();
    renderWorkroomArtifactContent();
  } catch (e) {
    alert(`保存失败：${e.message}`);
  }
}

async function submitArtifactForReview() {
  try {
    await apiPost(`/projects/${workroomProjectId}/artifacts/${workroomArtifactId}/submit-review`, {});
    await refreshDashboard();
    renderWorkroomShell(workroomProjectId, workroomArtifactId);
  } catch (e) {
    alert(`提交失败：${e.message}`);
  }
}

function renderArtifactEditorShell(art) {
  const content = workroomEditContent ?? art._viewContent ?? art.content ?? "";
  return `
    <div class="founder-doc-shell glass-inner art-doc-shell">
      <textarea class="founder-doc-editor art-doc-editor" id="art-editor-content" spellcheck="false">${escapeHtml(content)}</textarea>
    </div>`;
}

function renderWorkroomArtHead(art, opts = {}) {
  const { editing = false } = opts;
  const kindLabel = ART_KIND_LABELS[artifactKind(art)] || artifactKind(art);
  const headActions = editing
    ? `<div class="art-head-actions">${microBtn("x", "cancelArtifactEditor()", "取消")}${microBtn("check", "saveArtifactContent()", "保存", "micro-accent")}</div>`
    : renderArtifactExportMenu(art);
  return `
    <div class="workroom-art-head">
      <div class="workroom-art-title">
        <h2>${escapeHtml(art.title || "未命名交付")}</h2>
        <div class="workroom-art-sub">
          <span class="art-version">v${art.version || "0.1"}</span>
          <span class="art-kind-badge">${kindLabel}</span>
          ${art.format ? `<span class="art-format-badge">${art.format}</span>` : ""}
        </div>
      </div>
      ${headActions}
    </div>`;
}

async function reloadArtifactDiff() {
  const art = getArtifact(workroomArtifactId);
  if (!art || !workroomDiffMode) return;
  const versions = art.versions || [];
  if (versions.length < 2) {
    workroomDiffMode = false;
    workroomDiffLines = null;
    return;
  }
  const fromV = workroomDiffFrom || versions[Math.max(0, versions.length - 2)].version;
  const toV = workroomDiffTo || art.version;
  try {
    const json = await apiGet(
      `/projects/${workroomProjectId}/artifacts/${workroomArtifactId}/diff?from=${encodeURIComponent(fromV)}&to=${encodeURIComponent(toV)}`
    );
    workroomDiffLines = json.data.lines || [];
  } catch (_) {
    workroomDiffLines = null;
    workroomDiffMode = false;
  }
}

async function syncWorkroomAfterRefresh() {
  if (!workroomProjectId || document.getElementById("sheet-backdrop")?.hidden) return;
  await loadWorkroomData(workroomProjectId);
  if (isWorkroomUiInteractive()) return;
  const ui = captureWorkroomUiState();
  if (workroomData?.header) renderWorkroomHeader(workroomData.header);
  document.getElementById("workroom-nav").innerHTML = renderWorkroomNavGrouped(
    workroomProjectId,
    workroomArtifactId,
    workroomData
  );
  renderWorkroomFocus(workroomData);
  if (workroomDiffMode) await reloadArtifactDiff();
  renderWorkroomArtifactContent();
  restoreWorkroomUiState(ui);
}

function renderArtifactHitlBar(art) {
  if (art.status !== "review" || !art.hitlId) return "";
  return `<div class="art-hitl-bar"><span>📋 待你审批定稿</span></div>`;
}

async function approveArtifact(artifactId) {
  try {
    await apiPost(`/projects/${workroomProjectId}/artifacts/${artifactId}/approve`, {});
    await refreshDashboard();
    renderWorkroomShell(workroomProjectId, artifactId);
  } catch (e) {
    alert(`批准失败：${e.message}`);
  }
}

async function rejectArtifactHitl(artifactId, hitlId) {
  const note = prompt("驳回理由（可选）") || "需修改后重新提交";
  try {
    await apiPost(`/hitl/${hitlId}/reject`, { note });
    await refreshDashboard();
    renderWorkroomShell(workroomProjectId, artifactId);
  } catch (e) {
    alert(`驳回失败：${e.message}`);
  }
}

function renderVersionBar(art) {
  const versions = art.versions || [{ version: art.version || "0.1", note: "当前" }];
  const activeVer = workroomViewVersion || workroomDiffFrom || art.version || versions[versions.length - 1]?.version;
  const current = versions.find((v) => v.version === activeVer) || versions[versions.length - 1];
  const items = versions.map((v) =>
    `<button type="button" onclick="event.stopPropagation();pickArtifactVersion('${escapeAttr(v.version)}')">v${escapeHtml(v.version)} · ${escapeHtml(v.note || "")}</button>`
  ).join("");
  const diffTitle = workroomDiffMode ? "关闭对比" : "版本对比";
  return `
    <div class="art-version-bar">
      <div class="wr-dropdown" id="art-version-dd">
        <button type="button" class="version-pill" onclick="toggleDropdown('art-version-dd', event)" title="切换版本">
          <span>v${escapeHtml(current.version)} · ${escapeHtml(current.note || "")}</span>${WR_ICONS.chevronDown}
        </button>
        <div class="wr-dropdown-menu" onclick="event.stopPropagation()">${items}</div>
      </div>
      ${iconBtn("diff", "toggleArtifactDiff()", diffTitle, `icon-btn-sm${workroomDiffMode ? " icon-btn-active" : ""}`)}
    </div>`;
}

function pickArtifactVersion(version) {
  closeAllDropdowns();
  workroomViewVersion = version;
  workroomDiffFrom = version;
  if (!workroomDiffMode) loadArtifactVersionContent(version);
  else reloadArtifactDiff().then(() => renderWorkroomArtifactContent());
}

function onArtifactVersionChange(version) {
  pickArtifactVersion(version);
}

async function loadArtifactVersionContent(version) {
  try {
    const json = await apiGet(
      `/projects/${workroomProjectId}/artifacts/${workroomArtifactId}/content?version=${encodeURIComponent(version)}`
    );
    const art = getArtifact(workroomArtifactId);
    if (art) {
      art._viewContent = json.data.content;
      renderWorkroomArtifactContent();
    }
  } catch (_) {}
}

async function toggleArtifactDiff() {
  workroomEditMode = false;
  workroomEditContent = null;
  workroomDiffMode = !workroomDiffMode;
  if (!workroomDiffMode) {
    workroomDiffLines = null;
    workroomDiffFrom = null;
    workroomDiffTo = null;
    const art = getArtifact(workroomArtifactId);
    if (art) delete art._viewContent;
    renderWorkroomArtifactContent();
    return;
  }
  const art = getArtifact(workroomArtifactId);
  const versions = art?.versions || [];
  if (versions.length < 2) {
    alert("至少需要两个版本才能对比");
    workroomDiffMode = false;
    return;
  }
  workroomDiffFrom = workroomDiffFrom || versions[Math.max(0, versions.length - 2)].version;
  workroomDiffTo = art.version;
  await reloadArtifactDiff();
  renderWorkroomArtifactContent();
}

function renderDiffViewer(lines) {
  const html = (lines || []).map((line) => {
    let cls = "diff-line";
    if (line.startsWith("+") && !line.startsWith("+++")) cls += " diff-add";
    else if (line.startsWith("-") && !line.startsWith("---")) cls += " diff-del";
    else if (line.startsWith("@@")) cls += " diff-hunk";
    return `<div class="${cls}">${line.replace(/</g, "&lt;")}</div>`;
  }).join("");
  return `<div class="viewer-diff">${html || "<p>无差异</p>"}</div>`;
}

function renderNavGroupInner(g, activeId) {
  return `
    <div class="art-nav-group ${g.isCurrent ? "art-nav-group-current" : ""}">
      <div class="art-nav-group-head">
        <div class="art-nav-group-title">${escapeHtml(g.label || g.id)}${g.isCurrent ? '<span class="nav-current-badge">当前</span>' : ""}</div>
      </div>
      ${(g.fold || []).map(renderNavFold).join("")}
      ${(g.artifacts || []).map((a) => renderNavArtifactItem(a, activeId)).join("")}
    </div>`;
}

function renderWorkroomNavGrouped(projectId, activeId, payload) {
  const groups = payload?.groups;
  if (groups?.length) {
    const current = groups.filter((g) => g.isCurrent);
    const history = groups.filter(
      (g) => g.isHistory && ((g.artifacts || []).length || (g.fold || []).length)
    );
    const currentHtml = current.map((g) => renderNavGroupInner(g, activeId)).join("");
    const historyHtml = history.length
      ? `<details class="nav-stage-history" data-fold-key="stage-history">
          <summary>历史阶段 · ${history.length} 组</summary>
          <div class="nav-stage-history-body">${history.map((g) => renderNavGroupInner(g, activeId)).join("")}</div>
        </details>`
      : "";
    return currentHtml + historyHtml;
  }
  const arts = sortRoleTasksByRecency(data.artifacts.filter((a) => a.projectId === projectId));
  const byGroup = {};
  arts.forEach((a) => { (byGroup[artifactGroup(a)] = byGroup[artifactGroup(a)] || []).push(a); });
  if (!arts.length) return '<p class="nav-empty">暂无产出</p>';
  return ART_GROUP_ORDER.filter((g) => byGroup[g]?.length).map((g) => `
    <div class="art-nav-group">
      <div class="art-nav-group-title">${ART_GROUP_LABELS[g] || g}</div>
      ${byGroup[g].map((a) => renderNavArtifactItem(a, activeId)).join("")}
    </div>`).join("");
}

function renderNavArtifactItem(a, activeId) {
  const role = getRole(a.roleId);
  const kind = ART_KIND_LABELS[artifactKind(a)] || artifactKind(a);
  const dot = STATUS_DOT[a.statusDot] || STATUS_DOT.active;
  const avatar = renderRoleAvatarsNav([a.roleId], 1);
  return `
    <div class="art-item ${a.id === activeId ? "active" : ""}" role="button" tabindex="0" data-artifact-id="${a.id}"
      onclick="selectArtifact('${a.id}')"
      onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectArtifact('${a.id}')}">
      <span class="art-status-dot" title="${a.status || "draft"}">${dot}</span>
      <span class="art-item-body">
        <div class="art-item-title">${escapeHtml(a.title || "")}</div>
        <div class="art-meta">${kind} · v${a.version || "0.1"}${role ? ` · ${role.name}` : ""}</div>
      </span>
      ${avatar}
    </div>`;
}

function renderContractViewer(art) {
  const sections = extractMdSections(art.content);
  const toc = sections.filter((s) => s.level <= 2).map((s) =>
    `<a class="contract-toc-item" href="#" onclick="scrollToSection(${s.line});return false">${s.title}</a>`
  ).join("");
  return `
    <div class="viewer-contract">
      ${sections.length > 3 ? `<nav class="contract-toc">${toc}</nav>` : ""}
      <div class="viewer-contract-body md-content" id="artifact-md-body">${highlightPendingFields(simpleMarkdown(art.content || ""))}</div>
    </div>`;
}

function scrollToSection(lineIdx) {
  document.getElementById("artifact-md-body")?.scrollIntoView?.();
}

function renderPrdViewer(art) {
  return `<div class="viewer-prd md-content">${highlightPendingFields(simpleMarkdown(art.content || ""))}</div>`;
}

function renderChecklistViewer(art) {
  const html = simpleMarkdown(art.content || "")
    .replace(/<li>☐/g, '<li class="check-item open">☐')
    .replace(/<li>☑/g, '<li class="check-item done">☑');
  return `<div class="viewer-checklist md-content">${highlightPendingFields(html)}</div>`;
}

function renderEmailViewer(art) {
  const raw = art.content || "";
  const subjectMatch = raw.match(/^Subject:\s*(.+)$/m);
  const subject = subjectMatch ? subjectMatch[1] : art.title;
  const body = raw.replace(/^Subject:.*\n?/m, "").trim();
  return `
    <div class="viewer-email">
      <div class="email-header">
        <div><span class="email-k">Subject</span> ${subject}</div>
        <div><span class="email-k">From</span> ${getRole(art.roleId)?.name || "运营"} · ${typeof BRAND_NAME !== "undefined" ? BRAND_NAME : "Golden Mean Studio"}</div>
      </div>
      <div class="email-body">${highlightPendingFields(simpleMarkdown(body))}</div>
    </div>`;
}

function renderMemoViewer(art) {
  return `<div class="viewer-memo md-content">${highlightPendingFields(simpleMarkdown(art.content || ""))}</div>`;
}

function renderCodeViewer(art) {
  const files = art.files || [];
  if (!files.length) {
    return `<div class="viewer-code md-content">${highlightPendingFields(simpleMarkdown(art.content || ""))}</div>`;
  }
  if (!workroomSelectedFile) workroomSelectedFile = files[0].path;
  const active = files.find((f) => f.path === workroomSelectedFile) || files[0];
  const tree = files.map((f) =>
    `<button type="button" class="code-file ${f.path === active.path ? "active" : ""}" onclick="selectCodeFile('${f.path.replace(/'/g, "\\'")}')">${f.path}</button>`
  ).join("");
  return `
    <div class="viewer-code-split">
      <nav class="code-tree">${tree}</nav>
      <div class="code-panel">
        <div class="code-file-meta">${active.path}</div>
        <pre class="code-block"><code>${(active.content || "").replace(/</g, "&lt;")}</code></pre>
      </div>
    </div>
    <div class="md-content" style="margin-top:0.75rem">${highlightPendingFields(simpleMarkdown(art.content || ""))}</div>`;
}

function selectCodeFile(path) {
  workroomSelectedFile = path;
  renderWorkroomArtifactContent();
}

function renderGalleryViewer(art) {
  const images = art.images || [];
  if (!images.length) {
    return `<div class="viewer-gallery-empty md-content">${highlightPendingFields(simpleMarkdown(art.content || ""))}</div>`;
  }
  return `<div class="viewer-gallery">${images.map((img, i) => `
    <figure class="gallery-item">
      <img src="${img.url || img.src}" alt="${img.title || ""}" loading="lazy"/>
      <figcaption>${img.title || img.caption || `图 ${i + 1}`}</figcaption>
    </figure>`).join("")}</div>`;
}

function renderDemoViewer(art) {
  const url = art.demoUrl || (art.content || "").match(/https?:\/\/[^\s`)]+/)?.[0];
  const safeUrl = url && /^https?:\/\//.test(url) ? url : null;
  return `
    <div class="viewer-demo">
      ${safeUrl ? `<div class="demo-toolbar"><a class="demo-link" href="${safeUrl}" target="_blank" rel="noopener">↗ 新窗口打开</a></div>
        <iframe class="demo-frame" src="${safeUrl}" title="Demo" sandbox="allow-scripts allow-same-origin allow-forms"></iframe>` : ""}
      <div class="md-content">${highlightPendingFields(simpleMarkdown(art.content || ""))}</div>
    </div>`;
}

function renderArtifactBody(art) {
  switch (artifactViewer(art)) {
    case "contract": return renderContractViewer(art);
    case "prd": return renderPrdViewer(art);
    case "checklist": return renderChecklistViewer(art);
    case "email": return renderEmailViewer(art);
    case "memo": return renderMemoViewer(art);
    case "code": return renderCodeViewer(art);
    case "demo": return renderDemoViewer(art);
    case "gallery": return renderGalleryViewer(art);
    default: return `<div class="md-content">${highlightPendingFields(simpleMarkdown(art.content || ""))}</div>`;
  }
}

function getEnrichedArtifact(id) {
  const base = getArtifact(id);
  if (!base || !workroomData?.groups) return base;
  for (const g of workroomData.groups) {
    const found = (g.artifacts || []).find((a) => a.id === id);
    if (found) return { ...base, ...found };
  }
  return base;
}

function renderWorkroomArtifactContent() {
  const art = getEnrichedArtifact(workroomArtifactId);
  const el = document.getElementById("workroom-content");
  if (!el) return;
  if (!art) { el.innerHTML = "<p class='nav-empty'>选择左侧交付</p>"; return; }

  if (workroomEditMode) {
    el.innerHTML = `
      ${renderWorkroomArtHead(art, { editing: true })}
      ${renderArtifactQualityBar(art)}
      ${(art.versions || []).length ? renderVersionBar(art) : ""}
      ${renderArtifactEditorShell(art)}`;
    requestAnimationFrame(() => {
      const ta = document.getElementById("art-editor-content");
      ta?.focus();
      if (ta) ta.setSelectionRange(ta.value.length, ta.value.length);
    });
    return;
  }

  if (workroomDiffMode && workroomDiffLines) {
    el.innerHTML = `
      ${renderWorkroomArtHead(art)}
      ${renderArtifactQualityBar(art)}
      ${renderVersionBar(art)}
      ${renderDiffViewer(workroomDiffLines)}`;
    return;
  }

  const displayArt = { ...art, content: art._viewContent || art.content };
  el.innerHTML = `
    ${renderWorkroomArtHead(art)}
    ${renderArtifactHitlBar(art)}
    ${renderArtifactActionBar(art)}
    ${renderArtifactQualityBar(art)}
    ${(art.versions || []).length ? renderVersionBar(art) : ""}
    ${wrapArtifactBody(renderArtifactBody(displayArt), art)}`;
}

function wrapArtifactBody(html, art) {
  if (!artifactCanInlineEdit(art)) return html;
  return `<div class="art-viewer-editable" onclick="onArtifactContentClick(event)" title="点击编辑">${html}</div>`;
}

window.setProjectPriority = setProjectPriority;
window.saveBriefFromEditor = saveBriefFromEditor;
window.toggleBriefEditor = toggleBriefEditor;
window.toggleDropdown = toggleDropdown;
window.projectExport = projectExport;
window.artifactExport = artifactExport;
window.handleArtifactAction = handleArtifactAction;
window.onArtifactContentClick = onArtifactContentClick;
window.onBriefBodyClick = onBriefBodyClick;
window.isWorkroomUiInteractive = isWorkroomUiInteractive;
window.pickArtifactVersion = pickArtifactVersion;
