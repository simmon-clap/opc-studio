/**
 * Finance v2 — 经营 Tab（docs/FINANCE-V2.md）
 */

let pnlFilter = "all";
let financeExportOpen = false;
let financePeriodMenuOpen = false;
let financeDetailProjectId = null;

const PNL_FILTER = { all: "全部", healthy: "盈利", watch: "需关注", pipeline: "线索" };

function isFinanceUiInteractive() {
  if (financeExportOpen || financePeriodMenuOpen) return true;
  if (financeDetailProjectId) return true;
  const root = document.getElementById("costs-root");
  if (!root) return false;
  return !!root.querySelector("details[open], .fin-export-menu.open, .wr-dropdown.open");
}

function captureFinanceUiState() {
  const root = document.getElementById("costs-root");
  if (!root) return null;
  const openDetails = [...root.querySelectorAll("details[open]")].map((el) => el.dataset.finSection);
  return { openDetails, financeExportOpen, financePeriodMenuOpen, pnlFilter };
}

function restoreFinanceUiState(state) {
  if (!state) return;
  pnlFilter = state.pnlFilter || "all";
  financeExportOpen = !!state.financeExportOpen;
  financePeriodMenuOpen = !!state.financePeriodMenuOpen;
  const root = document.getElementById("costs-root");
  if (!root) return;
  (state.openDetails || []).forEach((id) => {
    const el = root.querySelector(`details[data-fin-section="${id}"]`);
    if (el) el.open = true;
  });
  if (financeExportOpen) root.querySelector(".fin-export-menu")?.classList.add("open");
  if (financePeriodMenuOpen) document.getElementById("fin-period-dd")?.classList.add("open");
}

function financePeriodLabel(c) {
  const p = c?.period || "";
  const t = c?.periodType || "month";
  if (t === "quarter" && p.includes("-Q")) {
    const [y, q] = p.toUpperCase().split("-Q");
    return `${y} 年第 ${q} 季度`;
  }
  if (p.length >= 7) return `${p.slice(0, 4)} 年 ${parseInt(p.slice(5, 7), 10)} 月`;
  return p;
}

function financePeriodOptions(c) {
  const cur = c?.period || "2026-05";
  const year = cur.slice(0, 4) || "2026";
  const monthOpts = [];
  for (let m = 1; m <= 12; m += 1) {
    const mm = String(m).padStart(2, "0");
    monthOpts.push({ value: `${year}-${mm}`, label: `${year} 年 ${m} 月` });
  }
  const quarterOpts = [1, 2, 3, 4].map((q) => ({
    value: `${year}-Q${q}`,
    label: `${year} 年第 ${q} 季度`,
  }));
  return c?.periodType === "quarter" ? quarterOpts : monthOpts;
}

async function setFinancePeriod(periodType, period) {
  try {
    await apiPatch("/finance/period", { periodType, period });
    await refreshDashboard();
    renderCosts();
  } catch (e) {
    alert(e.message || "期间切换失败");
  }
}

async function switchFinancePeriodType(type) {
  const c = data.costs || {};
  const cur = c.period || "2026-05";
  const year = cur.slice(0, 4) || "2026";
  let period = cur;
  if (type === "quarter") {
    const month = parseInt(cur.slice(5, 7) || "5", 10);
    period = `${year}-Q${Math.ceil(month / 3)}`;
  } else {
    period = `${year}-05`;
  }
  await setFinancePeriod(type, period);
}

function toggleFinanceExportMenu(ev) {
  ev?.stopPropagation();
  financeExportOpen = !financeExportOpen;
  financePeriodMenuOpen = false;
  document.getElementById("fin-period-dd")?.classList.remove("open");
  document.querySelector(".fin-export-menu")?.classList.toggle("open", financeExportOpen);
}

function closeFinanceMenus() {
  financeExportOpen = false;
  financePeriodMenuOpen = false;
  document.querySelectorAll(".fin-export-menu").forEach((el) => el.classList.remove("open"));
  document.getElementById("fin-period-dd")?.classList.remove("open");
}

function toggleFinPeriodMenu(ev) {
  ev?.stopPropagation();
  financePeriodMenuOpen = !financePeriodMenuOpen;
  financeExportOpen = false;
  document.getElementById("fin-period-dd")?.classList.toggle("open", financePeriodMenuOpen);
  document.querySelector(".fin-export-menu")?.classList.remove("open");
}

async function pickFinancePeriod(period) {
  closeFinanceMenus();
  const periodType = data.costs?.periodType || "month";
  await setFinancePeriod(periodType, period);
}

function resolveFinanceStatement(c) {
  const stmt = { ...(c.statement || {}) };
  const s = c.summary || {};
  const fallbacks = [
    ["revenue", "revenue"],
    ["costOfServices", "totalCost"],
    ["grossProfit", "margin"],
    ["grossMarginPct", "marginPct"],
    ["cashReceived", "received"],
    ["cashPending", "pending"],
  ];
  fallbacks.forEach(([key, src]) => {
    if (stmt[key] == null && s[src] != null) stmt[key] = s[src];
  });
  if (stmt.operatingExpenses == null) {
    const internal = (c.byProject || []).find((r) => r.projectId === "_internal");
    stmt.operatingExpenses = internal?.cost || 0;
  }
  if (stmt.operatingProfit == null && stmt.grossProfit != null) {
    stmt.operatingProfit = Number(stmt.grossProfit) - Number(stmt.operatingExpenses || 0);
  }
  return stmt;
}

function finNum(n) {
  const v = Number(n);
  return Number.isFinite(v) ? v : 0;
}

function renderFinanceOverview(c, s) {
  const stmt = resolveFinanceStatement(c);
  const rev = finNum(stmt.revenue);
  const cost = finNum(stmt.costOfServices);
  const gross = finNum(stmt.grossProfit);
  const opex = finNum(stmt.operatingExpenses);
  const profit = finNum(stmt.operatingProfit);
  const marginPct = stmt.grossMarginPct;
  const received = finNum(stmt.cashReceived);
  const pending = finNum(stmt.cashPending);
  const cashBase = received + pending || rev || 1;

  const costPct = rev > 0 ? Math.max(0, Math.min(100, (cost / rev) * 100)) : 0;
  const grossPct = rev > 0 ? Math.max(0, Math.min(100 - costPct, (gross / rev) * 100)) : 0;
  const budgetPct = s.monthlyBudget ? Math.min(100, Math.round((finNum(s.totalCost) / s.monthlyBudget) * 100)) : 0;
  const budgetWarn = budgetPct >= 80;

  return `
    <section class="fin-overview glass" aria-label="经营概览">
      <header class="fin-overview-head">
        <span class="fin-overview-title">损益摘要</span>
        ${marginPct != null ? `<span class="fin-margin-badge">毛利率 ${marginPct}%</span>` : ""}
      </header>

      <div class="fin-hero-metrics">
        <div class="fin-hero-item">
          <span class="fin-hero-label">营业收入</span>
          <span class="fin-hero-value">${fmtMoney(rev)}</span>
        </div>
        <div class="fin-hero-item fin-hero-accent">
          <span class="fin-hero-label">毛利</span>
          <span class="fin-hero-value">${fmtMoney(gross)}</span>
        </div>
        <div class="fin-hero-item">
          <span class="fin-hero-label">经营利润</span>
          <span class="fin-hero-value">${fmtMoney(profit)}</span>
        </div>
      </div>

      <div class="fin-stack" aria-hidden="true">
        <div class="fin-stack-track">
          ${costPct > 0 ? `<div class="fin-stack-seg cost" style="width:${Math.max(costPct, 4)}%" title="营业成本"><span>成本 ${fmtMoney(cost)}</span></div>` : ""}
          ${grossPct > 0 ? `<div class="fin-stack-seg gross" style="width:${Math.max(grossPct, 4)}%" title="毛利"><span>毛利 ${fmtMoney(gross)}</span></div>` : ""}
        </div>
        <div class="fin-stack-legend">
          <span><i class="dot cost"></i>营业成本 ${fmtMoney(cost)}</span>
          <span><i class="dot gross"></i>毛利 ${fmtMoney(gross)}</span>
        </div>
      </div>

      <div class="fin-detail-grid">
        <div class="fin-detail-cell">
          <span class="k">期间费用</span>
          <span class="v deduct">${fmtMoney(opex)}</span>
        </div>
        <div class="fin-detail-cell">
          <span class="k">已收现金</span>
          <span class="v">${fmtMoney(received)}</span>
          <div class="fin-mini-bar"><div class="fill received" style="width:${(received / cashBase) * 100}%"></div></div>
        </div>
        <div class="fin-detail-cell">
          <span class="k">待收现金</span>
          <span class="v">${fmtMoney(pending)}</span>
          <div class="fin-mini-bar"><div class="fill pending" style="width:${(pending / cashBase) * 100}%"></div></div>
        </div>
      </div>

      <div class="fin-token-meter${budgetWarn ? " warn" : ""}">
        <div class="fin-token-top">
          <span class="fin-token-label">Token 预算</span>
          <span class="fin-token-val">${fmtMoney(s.totalCost)}<span class="fin-token-of"> / ${fmtMoney(s.monthlyBudget)}</span></span>
        </div>
        <div class="fin-token-track"><div class="fin-token-fill" style="width:${budgetPct}%"></div></div>
        <div class="fin-token-foot">
          <span>${budgetPct}% 已用</span>
          <span>剩余 ${fmtMoney(s.budgetRemaining)}</span>
        </div>
      </div>

      ${stmt.taxAccrual ? `<p class="fin-tax-note">税费应计 ${fmtMoney(stmt.taxAccrual)}${stmt.taxRatePct != null ? ` · 税率 ${stmt.taxRatePct}%（法务）` : ""}</p>` : ""}
      <p class="fin-currency-note">${financePeriodLabel(c)} · 币种 ${c.currency || "CNY"} · 简化损益表</p>
    </section>`;
}

function renderFinanceToolbar(c) {
  const periodType = c.periodType || "month";
  const options = financePeriodOptions(c);
  const currentLabel = options.find((o) => o.value === c.period)?.label || financePeriodLabel(c);

  return `
    <div class="fin-toolbar glass-inner">
      <div class="fin-toolbar-left">
        <div class="fin-segment" role="tablist" aria-label="期间类型">
          <button type="button" role="tab" class="fin-segment-btn ${periodType === "month" ? "active" : ""}" aria-selected="${periodType === "month"}" onclick="switchFinancePeriodType('month')">月度</button>
          <button type="button" role="tab" class="fin-segment-btn ${periodType === "quarter" ? "active" : ""}" aria-selected="${periodType === "quarter"}" onclick="switchFinancePeriodType('quarter')">季度</button>
        </div>
        <div class="wr-dropdown fin-period-dd" id="fin-period-dd">
          <button type="button" class="fin-period-trigger" onclick="toggleFinPeriodMenu(event)" aria-haspopup="listbox">
            ${escapeHtml(currentLabel)}
            <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
          </button>
          <div class="wr-dropdown-menu fin-period-menu" role="listbox" onclick="event.stopPropagation()">
            ${options.map((o) => `
              <button type="button" class="${o.value === c.period ? "active" : ""}" onclick="pickFinancePeriod('${o.value}')">${escapeHtml(o.label)}</button>
            `).join("")}
          </div>
        </div>
      </div>
      <div class="fin-export-wrap">
        <button type="button" class="fin-export-trigger" onclick="toggleFinanceExportMenu(event)">
          导出 XLSX
          <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
        </button>
        <div class="fin-export-menu glass ${financeExportOpen ? "open" : ""}">
          <button type="button" onclick="exportFinanceXlsx()">完整财务报表（4 Sheet）</button>
        </div>
      </div>
    </div>`;
}

async function exportFinanceXlsx() {
  closeFinanceMenus();
  try {
    const period = data.costs?.period || "report";
    await downloadBlobFromApi("/finance/export?format=xlsx&scope=full", `opc-finance-${period}.xlsx`);
  } catch (e) {
    alert(e.message || "导出失败");
  }
}

function renderProjectPnLCard(row) {
  const p = getProject(row.projectId);
  const label = p?.clientName?.replace("（线索）", "") || row.label || row.projectId;
  const signed = row.revenue > 0;
  const advisory = row.advisory || row.note || "";
  return `
    <button type="button" class="pnl-card glass pnl-${row.health}" onclick="showProjectPnL('${row.projectId}')">
      <div class="pnl-card-top">
        <div class="pnl-name">${escapeHtml(label)}</div>
        <span class="pnl-health">${PNL_HEALTH[row.health] || row.health}</span>
      </div>
      <div class="pnl-metrics">
        <div><span class="k">合同</span><span>${signed ? fmtMoney(row.revenue) : row.quoted ? `报价 ${fmtMoney(row.quoted)}` : "—"}</span></div>
        <div><span class="k">已收</span><span>${fmtMoney(row.received || 0)}</span></div>
        <div><span class="k">总成本</span><span>${fmtMoney(row.cost)}</span></div>
        <div><span class="k">毛利</span><span class="${row.margin >= 0 ? "pos" : "neg"}">${signed || row.margin < 0 ? fmtMoney(row.margin) : "—"}${row.marginPct ? ` (${row.marginPct}%)` : ""}</span></div>
      </div>
      ${advisory ? `<div class="pnl-note fin-advisory">${escapeHtml(advisory)}</div>` : ""}
    </button>`;
}

function renderProjectPnLSection() {
  const rows = getProjectPnLRows().filter((r) => {
    if (pnlFilter === "all") return true;
    if (pnlFilter === "healthy") return r.health === "healthy" || r.health === "strong";
    return r.health === pnlFilter;
  });
  const watchCount = (data.costs?.meta?.watchProjectCount) ?? getProjectPnLRows().filter((r) => r.health === "watch").length;

  return `
    ${watchCount ? `<div class="budget-alert glass pnl-watch-alert">${watchCount} 个项目需关注 · 未签约或回款未覆盖成本</div>` : ""}
    <div class="filter-row" style="margin-bottom:0.65rem">
      ${Object.entries(PNL_FILTER).map(([id, label]) => `
        <button type="button" class="filter-chip filter-chip-sm ${pnlFilter === id ? "active" : ""}" onclick="setPnlFilter('${id}')">${label}</button>
      `).join("")}
    </div>
    <div class="pnl-grid">${rows.map(renderProjectPnLCard).join("") || '<p class="empty-inline">暂无</p>'}</div>`;
}

function renderProjectRoleCosts(byRole) {
  if (!byRole?.length) return '<p class="empty-inline">暂无角色成本汇总</p>';
  return `
    <div class="fin-role-table">
      ${byRole.map((row) => {
        const r = getRole(row.roleId);
        return `
        <div class="fin-role-row">
          <img src="../../assets/avatars/${row.roleId}.png" alt="" width="28" height="28"/>
          <span class="name">${escapeHtml(r?.name || row.roleId)}</span>
          <span class="tokens">${((row.tokens || 0) / 1000).toFixed(0)}k</span>
          <span class="cost">${fmtMoney(row.cost)}</span>
          <span class="pct">${row.sharePct || 0}%</span>
        </div>`;
      }).join("")}
    </div>`;
}

function renderCostBreakdown(bd) {
  if (!bd) return "";
  const rows = [
    ["Token", bd.token],
    ["外部", bd.external],
    ["税费", bd.tax],
    ["其他", bd.other],
  ].filter(([, v]) => v != null && v !== 0);
  if (!rows.length) return "";
  return `
    <details class="fin-breakdown">
      <summary>成本明细</summary>
      <div class="config-grid" style="margin-top:0.5rem">
        ${rows.map(([k, v]) => `<div class="config-row"><span class="k">${k}</span><span>${fmtMoney(v)}</span></div>`).join("")}
      </div>
    </details>`;
}

function showProjectPnL(projectId) {
  financeDetailProjectId = projectId;
  const row = getProjectPnL(projectId);
  const p = getProject(projectId);
  if (!row || !p) return;
  const signed = row.revenue > 0;
  const recvCover = row.cost > 0 && row.received ? (row.received / row.cost).toFixed(1) : null;
  const bd = row.costBreakdown || {};

  openModal(`
    <h2 style="font-size:1.05rem;font-weight:700">${escapeHtml(p.clientName.replace("（线索）", ""))} · 项目财务</h2>
    <div class="modal-stat-row">
      <div class="modal-stat"><div class="v">${signed ? fmtMoney(row.revenue) : "—"}</div><div class="l">合同</div></div>
      <div class="modal-stat"><div class="v">${fmtMoney(row.received || 0)}</div><div class="l">已收</div></div>
      <div class="modal-stat"><div class="v">${fmtMoney(row.cost)}</div><div class="l">总成本</div></div>
      <div class="modal-stat"><div class="v" style="color:${row.margin >= 0 ? "var(--green)" : "var(--red)"}">${fmtMoney(row.margin)}</div><div class="l">毛利</div></div>
    </div>
    <div class="config-grid" style="margin:0.75rem 0">
      <div class="config-row"><span class="k">健康度</span><span class="pnl-health-tag pnl-${row.health}">${PNL_HEALTH[row.health]}</span></div>
      ${row.quoted ? `<div class="config-row"><span class="k">报价</span><span>${fmtMoney(row.quoted)}</span></div>` : ""}
      ${row.pending ? `<div class="config-row"><span class="k">待收</span><span>${fmtMoney(row.pending)}</span></div>` : ""}
      ${recvCover ? `<div class="config-row"><span class="k">已收/成本</span><span>${recvCover}x</span></div>` : ""}
      ${row.marginPct != null ? `<div class="config-row"><span class="k">毛利率</span><span>${row.marginPct}%</span></div>` : ""}
    </div>
    ${renderCostBreakdown(bd)}
    <h3 class="fin-modal-section">按角色成本</h3>
    ${renderProjectRoleCosts(row.byRole)}
    ${row.advisory ? `<div class="focus-line fin-advisory-block"><strong>财务建议</strong><br>${escapeHtml(row.advisory)}</div>` : ""}
    <div class="btn-row" style="margin-top:1rem">
      <button class="btn-primary" onclick="closeFinanceDetail();openWorkroom('${projectId}')">进入工作室</button>
      ${signed ? `<button class="btn-secondary" onclick="closeFinanceDetail();showClientDetail('${p.clientId}')">客户档案</button>` : ""}
      <button class="btn-secondary" onclick="closeFinanceDetail()">关闭</button>
    </div>
  `, "wide");
}

function closeFinanceDetail() {
  financeDetailProjectId = null;
  closeModal();
}

function setPnlFilter(id) {
  pnlFilter = id;
  renderCosts();
}

function renderCosts() {
  const root = document.getElementById("costs-root");
  if (!root) return;
  const c = data.costs;
  if (!c) return;

  const saved = captureFinanceUiState();
  const s = c.summary || {};

  root.innerHTML = `
    ${renderFinanceToolbar(c)}
    ${s.budgetAlert ? `<div class="budget-alert glass">${escapeHtml(s.budgetAlertMessage || "Token 预算告警")}</div>` : ""}
    ${renderFinanceOverview(c, s)}
    <div class="cost-section">
      <h3>项目盈亏</h3>
      ${renderProjectPnLSection()}
    </div>
    <details class="cost-section" data-fin-section="roles">
      <summary><h3>按角色成本</h3></summary>
      <div class="role-cost-list" style="margin-top:0.65rem">
        ${(c.byRole || []).map((row) => {
          const r = getRole(row.roleId);
          const cfg = data.roleConfig?.find((x) => x.roleId === row.roleId);
          return `
          <button type="button" class="role-cost-row glass" onclick="showRoleConfig('${row.roleId}')">
            <img src="../../assets/avatars/${row.roleId}.png" alt=""/>
            <div class="info">
              <div class="name">${escapeHtml(r?.name || row.roleId)} · ${ROLE_SHORT[row.roleId] || row.roleId}</div>
              <div class="bar-wrap"><div class="bar" style="width:${row.sharePct}%"></div></div>
            </div>
            <div class="amt">
              <div class="c">${fmtMoney(row.cost)}</div>
              <div class="t">${((row.tokens || 0) / 1000).toFixed(0)}k · ${escapeHtml(cfg?.model || row.model || "")}</div>
            </div>
          </button>`;
        }).join("")}
      </div>
    </details>
    <details class="cost-section" data-fin-section="weekly">
      <summary><h3>近四周 Token</h3></summary>
      <div class="week-bars glass" style="padding:1rem;border-radius:14px;margin-top:0.65rem">
        ${(() => {
          const weeks = c.weekly || [];
          const maxWeek = Math.max(...weeks.map((w) => w.cost), 1);
          return weeks.map((w) => `
            <div class="week-bar">
              <div class="bar" style="height:${Math.max(12, (w.cost / maxWeek) * 64)}px"></div>
              <span class="lbl">${escapeHtml(String(w.week).replace("2026-", ""))}</span>
            </div>`).join("");
        })()}
      </div>
    </details>`;

  restoreFinanceUiState(saved);

  if (!root.dataset.finBound) {
    root.dataset.finBound = "1";
    document.addEventListener("click", (ev) => {
      if (!ev.target.closest(".fin-export-wrap, .fin-period-dd")) closeFinanceMenus();
    });
  }
}

window.renderCosts = renderCosts;
window.showProjectPnL = showProjectPnL;
window.setPnlFilter = setPnlFilter;
window.isFinanceUiInteractive = isFinanceUiInteractive;
window.setFinancePeriod = setFinancePeriod;
window.switchFinancePeriodType = switchFinancePeriodType;
window.exportFinanceXlsx = exportFinanceXlsx;
window.toggleFinanceExportMenu = toggleFinanceExportMenu;
window.toggleFinPeriodMenu = toggleFinPeriodMenu;
window.pickFinancePeriod = pickFinancePeriod;
window.closeFinanceDetail = closeFinanceDetail;
