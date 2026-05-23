/** Workroom v0.3 — grouped nav, typed viewers, versions, HITL */

const ART_GROUP_ORDER = ["evaluate", "legal", "engineering", "delivery", "ops"];
const ART_GROUP_LABELS = {
  evaluate: "评估 · 立项",
  legal: "法务 · 合同",
  engineering: "工程 · 交付",
  delivery: "验收 · 结项",
  ops: "运营 · 台账",
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
    memo: "evaluate", prd: "evaluate",
    nda: "legal", contract: "legal", sow: "legal", quote: "legal",
    tech_spec: "engineering", code: "engineering", demo: "engineering", design: "engineering",
    acceptance: "delivery", closure: "delivery", email: "delivery",
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

function renderArtifactHitlBar(art) {
  if (art.status !== "review" || !art.hitlId) return "";
  return `
    <div class="art-hitl-bar">
      <span>📋 待你审批定稿</span>
      <div class="art-hitl-actions">
        <button class="btn-primary btn-sm" onclick="approveArtifact('${art.id}')">批准定稿</button>
        <button class="btn-secondary btn-sm" onclick="rejectArtifactHitl('${art.id}','${art.hitlId}')">驳回</button>
      </div>
    </div>`;
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
  const opts = versions.map((v) =>
    `<option value="${v.version}">v${v.version} · ${v.note || ""}</option>`
  ).join("");
  return `
    <div class="art-version-bar">
      <label>版本 <select id="art-version-select" onchange="onArtifactVersionChange(this.value)">${opts}</select></label>
      <button class="btn-secondary btn-sm" onclick="toggleArtifactDiff()">${workroomDiffMode ? "关闭对比" : "版本对比"}</button>
    </div>`;
}

function onArtifactVersionChange(version) {
  workroomDiffFrom = version;
  if (!workroomDiffMode) loadArtifactVersionContent(version);
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
  workroomDiffMode = !workroomDiffMode;
  if (!workroomDiffMode) {
    const art = getArtifact(workroomArtifactId);
    if (art) delete art._viewContent;
    delete art._diffLines;
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
  const fromV = workroomDiffFrom || versions[Math.max(0, versions.length - 2)].version;
  const toV = art.version;
  try {
    const json = await apiGet(
      `/projects/${workroomProjectId}/artifacts/${workroomArtifactId}/diff?from=${encodeURIComponent(fromV)}&to=${encodeURIComponent(toV)}`
    );
    art._diffLines = json.data.lines || [];
    renderWorkroomArtifactContent();
  } catch (e) {
    alert(`对比失败：${e.message}`);
    workroomDiffMode = false;
  }
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

function renderWorkroomNavGrouped(projectId, activeId) {
  const arts = sortRoleTasksByRecency(data.artifacts.filter((a) => a.projectId === projectId));
  const byGroup = {};
  arts.forEach((a) => { (byGroup[artifactGroup(a)] = byGroup[artifactGroup(a)] || []).push(a); });
  if (!arts.length) return '<p style="font-size:0.78rem;color:var(--text3);padding:0.5rem">暂无产出</p>';
  return ART_GROUP_ORDER.filter((g) => byGroup[g]?.length).map((g) => `
    <div class="art-nav-group">
      <div class="art-nav-group-title">${ART_GROUP_LABELS[g] || g}</div>
      ${byGroup[g].map((a) => {
        const role = getRole(a.roleId);
        const kind = ART_KIND_LABELS[artifactKind(a)] || artifactKind(a);
        const st = a.status === "approved" ? " ✓" : a.status === "review" ? " ⏳" : a.status === "revision" ? " ↻" : "";
        return `
        <button class="art-item ${a.id === activeId ? "active" : ""}" onclick="selectArtifact('${a.id}')">
          <span class="art-ico">${ART_ICONS[a.icon] || ART_ICONS.doc}</span>
          <span>
            <div class="art-item-title">${a.title}${st}</div>
            <div class="art-meta">${kind} · ${role?.name || ""} · v${a.version || "0.1"}</div>
          </span>
        </button>`;
      }).join("")}
    </div>`).join("");
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

function renderWorkroomArtifactContent() {
  const art = getArtifact(workroomArtifactId);
  const el = document.getElementById("workroom-content");
  if (!el) return;
  if (!art) { el.innerHTML = "<p style='color:var(--text3)'>选择左侧文档</p>"; return; }

  if (workroomDiffMode && art._diffLines) {
    el.innerHTML = `${renderArtifactQualityBar(art)}${renderVersionBar(art)}${renderDiffViewer(art._diffLines)}`;
    return;
  }

  const displayArt = { ...art, content: art._viewContent || art.content };
  const kindLabel = ART_KIND_LABELS[artifactKind(art)] || artifactKind(art);
  el.innerHTML = `
    <div class="workroom-toolbar">
      <div class="workroom-meta">
        <span class="art-version">v${art.version || "0.1"}</span>
        <span class="art-kind-badge">${kindLabel}</span>
        ${art.format ? `<span class="art-format-badge">${art.format}</span>` : ""}
      </div>
      <div style="display:flex;gap:0.35rem">
        <button class="export-btn" style="width:auto;padding:0 0.65rem;font-size:0.72rem" onclick="exportCurrentMd()">MD</button>
        <button class="export-btn" style="width:auto;padding:0 0.65rem;font-size:0.72rem" onclick="exportCurrentPdf()">PDF</button>
      </div>
    </div>
    ${renderArtifactHitlBar(art)}
    ${renderArtifactQualityBar(art)}
    ${(art.versions || []).length ? renderVersionBar(art) : ""}
    ${renderArtifactBody(displayArt)}`;
}

function renderWorkroomBriefPanel(projectId) {
  const panel = document.getElementById("workroom-brief-panel");
  if (!panel || !projectId) return;
  const brief = (data?.projectBriefs || {})[projectId];
  if (!brief || (!brief.confirmedFacts?.length && !brief.openQuestions?.length && !brief.scope && !brief.cooperationMode)) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  const facts = (brief.confirmedFacts || []).map((f) => `<li>${escapeHtml(f)}</li>`).join("");
  const questions = (brief.openQuestions || []).map((q) => `<li class="brief-question">${escapeHtml(q)}</li>`).join("");
  panel.innerHTML = `
    <div class="workroom-panel-head">
      <div class="workroom-panel-title">项目 Brief</div>
      ${brief.updatedAt ? `<div class="workroom-panel-sub">更新 ${brief.updatedAt}</div>` : ""}
    </div>
    ${brief.cooperationMode || brief.ndaType || brief.scope ? `
    <div class="brief-meta-row">
      ${brief.cooperationMode ? `<span class="chip">${escapeHtml(brief.cooperationMode)}</span>` : ""}
      ${brief.ndaType ? `<span class="chip">${escapeHtml(brief.ndaType)}</span>` : ""}
      ${brief.scope ? `<span class="brief-scope">${escapeHtml(brief.scope)}</span>` : ""}
    </div>` : ""}
    ${facts ? `<ul class="brief-facts">${facts}</ul>` : ""}
    ${questions ? `<div class="brief-questions"><span class="brief-q-label">待确认</span><ul>${questions}</ul></div>` : ""}`;
}

function renderWorkroomNextSteps(projectId) {
  const panel = document.getElementById("workroom-next-panel");
  if (!panel || !projectId) return;
  apiGet(`/projects/${projectId}/next-steps`)
    .then((res) => {
      const steps = res.data || [];
      if (!steps.length) {
        panel.hidden = true;
        return;
      }
      panel.hidden = false;
      const priorityLabel = { high: "高", medium: "中", low: "低" };
      panel.innerHTML = `
        <div class="workroom-panel-head">
          <div class="workroom-panel-title">下一步</div>
          <div class="workroom-panel-sub">流程 cue · ${steps.length} 项</div>
        </div>
        <div class="next-steps-list">
          ${steps.map((s) => {
            const click = s.artifactId
              ? `onclick="selectArtifact('${s.artifactId}')"`
              : s.commitmentId
                ? ""
                : "";
            return `
            <button type="button" class="next-step-item priority-${s.priority || "medium"}" ${click}>
              <span class="next-step-priority">${priorityLabel[s.priority] || "中"}</span>
              <span class="next-step-msg">${escapeHtml(s.message)}</span>
            </button>`;
          }).join("")}
        </div>`;
    })
    .catch(() => { panel.hidden = true; });
}
