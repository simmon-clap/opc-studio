/** Weekly report v2 — list + detail modal, interaction-safe pulse sync */

const RISK_DOT = { high: "🔴", medium: "🟡", low: "🟢" };
const WEEKLY_LIST_VISIBLE = 8;

let weeklyDetailId = null;
let weeklyShowOlder = false;
let weeklyOpenDetails = new Set();

function getWeeklyReports() {
  const list = data?.weeklyReports;
  if (Array.isArray(list) && list.length) return list;
  if (data?.weeklyReport) return [data.weeklyReport];
  return [];
}

function getWeeklyReport(id) {
  return getWeeklyReports().find((r) => r.id === id || r.week === id) || null;
}

function isWeeklyUiInteractive() {
  if (weeklyDetailId && !document.getElementById("modal-backdrop")?.hidden) return true;
  if (document.querySelector("#weekly-root details[open]")) return true;
  return false;
}

function captureWeeklyUiState() {
  return {
    detailId: weeklyDetailId,
    showOlder: weeklyShowOlder,
    openDetails: [...document.querySelectorAll("#weekly-root details[data-wk-fold]")]
      .filter((d) => d.open)
      .map((d) => d.dataset.wkFold),
  };
}

function restoreWeeklyUiState(ui) {
  if (!ui) return;
  weeklyShowOlder = ui.showOlder;
  if (ui.detailId && !document.getElementById("modal-backdrop")?.hidden) {
    weeklyDetailId = ui.detailId;
    renderWeeklyDetailModal(ui.detailId, { restoreOnly: true });
  }
  (ui.openDetails || []).forEach((key) => {
    document.querySelector(`#weekly-root details[data-wk-fold="${CSS.escape(key)}"]`)?.setAttribute("open", "");
  });
}

function weeklyStatusLabel(status) {
  if (status === "draft") return "草稿";
  if (status === "sent") return "已发送";
  return status || "";
}

function renderWeeklyBlockHeader(block) {
  const roleId = block.roleId || "ceo";
  const src = typeof avatarSrc === "function" ? avatarSrc(roleId) : `../../assets/avatars/${roleId}.png`;
  const name = typeof avatarLabel === "function" ? avatarLabel(roleId) : (typeof getRole === "function" ? getRole(roleId)?.name : roleId) || roleId;
  return `
    <div class="wk-block-head">
      <img class="wk-block-avatar" src="${src}" alt="${escapeHtml(name)}" title="${escapeHtml(name)}"/>
      <div class="wk-block-head-text">
        <h3>${escapeHtml(block.title || "")}</h3>
        <span class="wk-block-role">${escapeHtml(name)}</span>
      </div>
    </div>`;
}

function renderWeeklySummaryHead(report) {
  const roleId = report.author || "ceo";
  const src = typeof avatarSrc === "function" ? avatarSrc(roleId) : `../../assets/avatars/${roleId}.png`;
  const name = typeof avatarLabel === "function" ? avatarLabel(roleId) : roleId;
  return `
    <div class="wk-summary-head">
      <img class="wk-block-avatar" src="${src}" alt="${escapeHtml(name)}" title="${escapeHtml(name)}"/>
      <div>
        <span class="wk-summary-label">CEO 总述</span>
        <span class="wk-block-role">${escapeHtml(name)}</span>
      </div>
    </div>`;
}

function weeklyRoleName(roleId) {
  if (typeof avatarLabel === "function") return avatarLabel(roleId);
  if (typeof getRole === "function") return getRole(roleId)?.name || roleId;
  return roleId || "";
}

function renderProjectRoleTag(roleId) {
  if (!roleId) return "";
  const src = typeof avatarSrc === "function" ? avatarSrc(roleId) : `../../assets/avatars/${roleId}.png`;
  const name = weeklyRoleName(roleId);
  return `<span class="wk-project-role" title="${escapeHtml(name)}"><img src="${src}" alt="${escapeHtml(name)}"/><span>${escapeHtml(name)}</span></span>`;
}

function renderProjectsBlock(block) {
  const items = (block.items || []).slice(0, 5);
  return `
    ${renderWeeklyBlockHeader(block)}
    <ul class="wk-project-list">
      ${items.map((item) => `
        <li class="wk-project-row">
          <div class="wk-project-top">
            <div class="wk-project-left">
              ${renderProjectRoleTag(item.roleId)}
              <span class="wk-project-label">${escapeHtml(item.label || "")}</span>
            </div>
            <span class="wk-project-pct">${item.progress || 0}%</span>
          </div>
          <div class="pipeline-bar-wrap"><div class="pipeline-bar" style="width:${Math.min(100, item.progress || 0)}%"></div></div>
          <p class="wk-project-text">${escapeHtml(item.text || "")}</p>
        </li>`).join("")}
    </ul>`;
}

function renderRisksBlock(block) {
  const items = (block.items || []).slice(0, 3);
  return `
    ${renderWeeklyBlockHeader(block)}
    <ul class="wk-bullet-list">
      ${items.map((item) => `
        <li><span class="wk-risk-dot">${RISK_DOT[item.level] || RISK_DOT.medium}</span>${escapeHtml(item.text || "")}</li>`).join("")}
    </ul>`;
}

function renderFinanceBlock(block) {
  const metrics = (block.metrics || []).slice(0, 2);
  return `
    ${renderWeeklyBlockHeader(block)}
    <p class="wk-finance-text">${escapeHtml(block.text || "")}</p>
    ${metrics.length ? `<div class="wk-finance-metrics">${metrics.map((m) =>
      `<span class="wk-metric"><span class="k">${escapeHtml(m.label)}</span>${escapeHtml(m.value)}</span>`
    ).join("")}</div>` : ""}
    ${block.costsLink ? `<button type="button" class="wk-link-btn" onclick="closeWeeklyDetail();goToView('costs')">查看经营明细 →</button>` : ""}`;
}

function renderOutlookBlock(block) {
  const items = (block.items || []).slice(0, 3);
  return `
    ${renderWeeklyBlockHeader(block)}
    <ol class="wk-outlook-list">
      ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ol>`;
}

function renderHighlightsBlock(block, reportId) {
  const foldKey = `${reportId}-highlights`;
  const roleId = block.roleId || "ceo";
  const src = typeof avatarSrc === "function" ? avatarSrc(roleId) : `../../assets/avatars/${roleId}.png`;
  const name = typeof avatarLabel === "function" ? avatarLabel(roleId) : roleId;
  const items = (block.items || []).slice(0, 5);
  const body = items.map((item) => {
    const rid = item.roleId || "ceo";
    const iname = weeklyRoleName(rid);
    const isrc = typeof avatarSrc === "function" ? avatarSrc(rid) : `../../assets/avatars/${rid}.png`;
    return `
      <li class="wk-highlight-row">
        <img class="wk-highlight-avatar" src="${isrc}" alt="${escapeHtml(iname)}" title="${escapeHtml(iname)}"/>
        <span class="wk-highlight-text">${escapeHtml(item.text || "")}</span>
      </li>`;
  }).join("");
  return `
    <details class="wk-fold" data-wk-fold="${escapeAttr(foldKey)}" ${block.collapsed !== false ? "" : "open"}>
      <summary class="wk-fold-summary">
        <img class="wk-block-avatar" src="${src}" alt="${escapeHtml(name)}"/>
        <span class="wk-fold-title">${escapeHtml(block.title || "部门一句")}</span>
      </summary>
      <ul class="wk-highlight-list">${body}</ul>
    </details>`;
}

function renderWeeklyBlocks(report) {
  const blocks = report.blocks || [];
  return blocks.map((block) => {
    let inner = "";
    switch (block.kind) {
      case "projects": inner = renderProjectsBlock(block); break;
      case "risks": inner = renderRisksBlock(block); break;
      case "finance": inner = renderFinanceBlock(block); break;
      case "outlook": inner = renderOutlookBlock(block); break;
      case "highlights": inner = renderHighlightsBlock(block, report.id || report.week); break;
      default: inner = `${renderWeeklyBlockHeader(block)}<p class="wk-muted">${escapeHtml(block.text || "")}</p>`;
    }
    const cls = block.kind === "highlights" ? "wk-block wk-block-fold" : "wk-block glass-inner";
    return `<section class="${cls}">${inner}</section>`;
  }).join("");
}

function weeklyOverviewStats(report) {
  const blocks = report?.blocks || [];
  const projects = (blocks.find((b) => b.kind === "projects")?.items || []).length;
  const risks = (blocks.find((b) => b.kind === "risks")?.items || []).filter(
    (i) => i.level === "high" || i.level === "medium"
  ).length;
  return { projects, risks };
}

function getCurrentWeeklyReport() {
  const reports = getWeeklyReports();
  const draft = reports.find((r) => r.status === "draft");
  if (draft) return draft;
  return [...reports].sort((a, b) => (b.week || "").localeCompare(a.week || ""))[0] || null;
}

function renderWeeklyOverview(report) {
  if (!report) return "";
  const id = report.id || report.week;
  const stats = weeklyOverviewStats(report);
  const src = typeof avatarSrc === "function" ? avatarSrc("ceo") : "../../assets/avatars/ceo.png";
  return `
    <button type="button" class="wk-overview glass" onclick="openWeeklyDetail('${escapeAttr(id)}')">
      <img class="wk-overview-avatar" src="${src}" alt="CEO"/>
      <div class="wk-overview-main">
        <div class="wk-overview-line">
          <span class="wk-overview-week">${escapeHtml(report.week || id)}</span>
          <span class="weekly-status st-${report.status || "draft"}">${weeklyStatusLabel(report.status)}</span>
        </div>
        <div class="wk-overview-period">${escapeHtml(report.period || "")}</div>
        <p class="wk-overview-summary">${escapeHtml(report.summary || "")}</p>
      </div>
      <div class="wk-overview-chips">
        <span class="wk-chip">${stats.projects} 项目在跟</span>
        ${stats.risks ? `<span class="wk-chip wk-chip-warn">${stats.risks} 项需关注</span>` : `<span class="wk-chip wk-chip-ok">风险可控</span>`}
      </div>
    </button>`;
}
function renderWeeklyListCard(report) {
  const id = report.id || report.week;
  const summary = (report.summary || "").slice(0, 72);
  return `
    <button type="button" class="wk-list-card glass" onclick="openWeeklyDetail('${escapeAttr(id)}')">
      <div class="wk-list-head">
        <span class="wk-list-week">${escapeHtml(report.week || id)}</span>
        <span class="weekly-status st-${report.status || "draft"}">${weeklyStatusLabel(report.status)}</span>
      </div>
      <div class="wk-list-period">${escapeHtml(report.period || "")}</div>
      <p class="wk-list-summary">${escapeHtml(summary)}${(report.summary || "").length > 72 ? "…" : ""}</p>
    </button>`;
}

function renderWeekly() {
  const root = document.getElementById("weekly-root");
  if (!root) return;
  const ui = captureWeeklyUiState();
  const reports = getWeeklyReports();
  if (!reports.length) {
    root.innerHTML = `<p class="wk-empty">暂无周报</p>`;
    return;
  }

  const current = getCurrentWeeklyReport();
  const sorted = [...reports].sort((a, b) => (b.week || "").localeCompare(a.week || ""));
  const histSorted = sorted.filter((r) => {
    if (!current) return true;
    return r.id !== current.id && r.week !== current.week;
  });
  const visible = weeklyShowOlder ? histSorted : histSorted.slice(0, WEEKLY_LIST_VISIBLE);
  const hiddenCount = Math.max(0, histSorted.length - WEEKLY_LIST_VISIBLE);

  root.innerHTML = `
    <div class="wk-section-label">本期概览</div>
    ${current ? renderWeeklyOverview(current) : ""}
    <div class="wk-history">
      <div class="wk-history-label">历史周报</div>
      ${visible.length ? visible.map((r) => renderWeeklyListCard(r)).join("") : '<p class="wk-empty-inline">暂无更早记录</p>'}
      ${!weeklyShowOlder && hiddenCount > 0
    ? `<button type="button" class="wk-show-older" onclick="toggleWeeklyOlder(true)">更早 ${hiddenCount} 期 ▾</button>`
    : weeklyShowOlder && histSorted.length > WEEKLY_LIST_VISIBLE
      ? `<button type="button" class="wk-show-older" onclick="toggleWeeklyOlder(false)">收起 ▴</button>`
      : ""}
    </div>`;

  restoreWeeklyUiState({ ...ui, detailId: null });
}

function toggleWeeklyOlder(show) {
  weeklyShowOlder = show;
  renderWeekly();
}

function renderWeeklyDetailModal(reportId, opts = {}) {
  const report = getWeeklyReport(reportId);
  if (!report) return;
  weeklyDetailId = reportId;
  const id = report.id || report.week;
  const canSend = report.status === "draft";
  const snap = report.snapshotAt || report.generatedAt;

  const html = `
    <div class="wk-modal">
      <header class="wk-modal-head">
        <div>
          <h2>${escapeHtml(report.week || id)}</h2>
          <div class="wk-modal-meta">
            <span>${escapeHtml(report.period || "")}</span>
            <span class="weekly-status st-${report.status}">${weeklyStatusLabel(report.status)}</span>
          </div>
        </div>
        <div class="wk-modal-toolbar">
          ${canSend ? `<button type="button" class="btn-primary btn-sm wk-send-btn" id="weekly-send-btn" onclick="sendWeeklyReport()">发送</button>` : ""}<button type="button" class="btn-secondary btn-sm wk-close-btn" onclick="closeWeeklyDetail()">关闭</button>
        </div>
      </header>
      <div class="wk-summary-block glass-inner">
        ${renderWeeklySummaryHead(report)}
        <p class="wk-summary">${escapeHtml(report.summary || "")}</p>
      </div>
      <div class="wk-modal-body">${renderWeeklyBlocks(report)}</div>
      <footer class="wk-modal-foot">
        ${snap ? `<span>基于 ${new Date(snap).toLocaleString("zh-CN")} 快照</span>` : ""}
        ${report.status === "sent" ? "<span>已冻结 · 只读</span>" : ""}
      </footer>
    </div>`;

  if (opts.restoreOnly) {
    document.getElementById("modal-body").innerHTML = html;
    return;
  }
  openModal(html, "wide weekly-modal");
  const closeBtn = document.getElementById("modal-close");
  if (closeBtn) closeBtn.hidden = true;
}

function openWeeklyDetail(reportId) {
  renderWeeklyDetailModal(reportId);
}

function closeWeeklyDetail() {
  weeklyDetailId = null;
  const closeBtn = document.getElementById("modal-close");
  if (closeBtn) closeBtn.hidden = false;
  closeModal();
}

function goToWeeklyAndOpen(reportId) {
  goToView("weekly");
  requestAnimationFrame(() => openWeeklyDetail(reportId));
}

async function sendWeeklyReport() {
  const report = getWeeklyReport(weeklyDetailId);
  if (!report || report.status === "sent") return;
  const btn = document.getElementById("weekly-send-btn");
  if (btn) { btn.disabled = true; btn.classList.add("is-busy"); }
  try {
    await apiPost("/weekly/current/send", {});
    await refreshDashboard();
    updateBadges();
    renderWeekly();
    if (weeklyDetailId) renderWeeklyDetailModal(weeklyDetailId);
    else closeWeeklyDetail();
  } catch (e) {
    alert(`发送失败：${e.message}`);
  } finally {
    if (btn) { btn.disabled = false; btn.classList.remove("is-busy"); }
  }
}

async function exportWeeklyPdf() {
  const report = getWeeklyReport(weeklyDetailId) || data.weeklyReport;
  if (!report) return;
  const bodyHtml = `
    <p><strong>总述</strong></p><p>${pdfEscapeHtml(report.summary || "")}</p>
    ${(report.blocks || []).map((block) => {
      if (block.kind === "projects") {
        return `<h2>${pdfEscapeHtml(block.title)}</h2><ul>${(block.items || []).map((i) =>
          `<li>${pdfEscapeHtml(i.label)} ${i.progress}% — ${pdfEscapeHtml(i.text)}</li>`).join("")}</ul>`;
      }
      if (block.kind === "risks") {
        return `<h2>${pdfEscapeHtml(block.title)}</h2><ul>${(block.items || []).map((i) =>
          `<li>${pdfEscapeHtml(i.text)}</li>`).join("")}</ul>`;
      }
      if (block.kind === "finance") {
        return `<h2>${pdfEscapeHtml(block.title)}</h2><p>${pdfEscapeHtml(block.text)}</p>`;
      }
      if (block.kind === "outlook") {
        return `<h2>${pdfEscapeHtml(block.title)}</h2><ol>${(block.items || []).map((i) =>
          `<li>${pdfEscapeHtml(i)}</li>`).join("")}</ol>`;
      }
      return "";
    }).join("")}`;
  const node = buildPdfExportNode({
    title: `${BRAND_NAME} CEO 周报 ${report.week}`,
    subtitle: `${report.period} · ${new Date(report.generatedAt || Date.now()).toLocaleString("zh-CN")}`,
    bodyHtml,
  });
  try {
    await exportHtmlToPdf(node, `weekly_${report.week}.pdf`);
  } catch (e) {
    alert(`PDF 导出失败：${e.message}`);
  }
}

function exportWeeklyMd() {
  const report = getWeeklyReport(weeklyDetailId) || data.weeklyReport;
  if (!report) return;
  const lines = [`# ${BRAND_NAME} 周报 ${report.week}`, "", report.period, "", report.summary, ""];
  (report.blocks || []).forEach((block) => {
    lines.push(`## ${block.title}`);
    if (block.kind === "projects") {
      (block.items || []).forEach((i) => lines.push(`- ${i.label} ${i.progress}% — ${i.text}`));
    } else if (block.kind === "risks") {
      (block.items || []).forEach((i) => lines.push(`- ${i.text}`));
    } else if (block.kind === "finance") {
      lines.push(block.text || "");
    } else if (block.kind === "outlook") {
      (block.items || []).forEach((item, idx) => lines.push(`${idx + 1}. ${item}`));
    } else if (block.kind === "highlights") {
      (block.items || []).forEach((i) => lines.push(`- ${i.roleId}: ${i.text}`));
    }
    lines.push("");
  });
  downloadBlob(lines.join("\n"), `weekly_${report.week}.md`, "text/markdown;charset=utf-8");
}

function escapeHtml(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeAttr(s) {
  return String(s || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

window.renderWeekly = renderWeekly;
window.openWeeklyDetail = openWeeklyDetail;
window.closeWeeklyDetail = closeWeeklyDetail;
window.goToWeeklyAndOpen = goToWeeklyAndOpen;
window.isWeeklyUiInteractive = isWeeklyUiInteractive;
window.toggleWeeklyOlder = toggleWeeklyOlder;
window.sendWeeklyReport = sendWeeklyReport;
window.exportWeeklyPdf = exportWeeklyPdf;
window.exportWeeklyMd = exportWeeklyMd;
