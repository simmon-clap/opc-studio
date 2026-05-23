/**
 * Settings v2 — 系统 / 角色 segment（docs/SETTINGS-V2.md）
 */

let stgSegment = "system";
let stgRoleId = "ceo";
let stgRoleConfigs = [];
let stgRegistry = [];
let stgRuntimeSettings = null;
let stgNewRoleOpen = false;
let stgProfilePreviewOn = false;
let stgFounderPreviewOn = false;
let stgOrchestrationOpen = false;
let stgSkillImportOpen = false;
let stgMcpOpen = false;

const STG_API_PRESETS = {
  OpenRouter: "https://openrouter.ai/api/v1",
  OpenAI: "https://api.openai.com/v1",
  Anthropic: "https://api.anthropic.com/v1",
  Moonshot: "https://api.moonshot.cn/v1",
  DeepSeek: "https://api.deepseek.com/v1",
  Ollama: "http://127.0.0.1:11434/v1",
  Custom: "",
};

const STG_CAPABILITIES = [
  { id: "text", label: "文本" },
  { id: "image", label: "图像" },
  { id: "video", label: "视频" },
  { id: "code", label: "代码" },
];

function isSettingsUiInteractive() {
  if (stgNewRoleOpen) return true;
  if (stgSkillImportOpen || stgMcpOpen) return true;
  const root = document.getElementById("settings-root");
  if (!root) return false;
  if (root.querySelector(".stg-modal.open, .founder-doc-editor:focus, .stg-role-profile:focus")) return true;
  if (stgFounderPreviewOn || stgProfilePreviewOn) return true;
  return !!root.querySelector("details[open]");
}

function captureSettingsUiState() {
  return {
    stgSegment,
    stgRoleId,
    stgNewRoleOpen,
    stgOrchestrationOpen,
    stgFounderPreviewOn,
    stgProfilePreviewOn,
  };
}

function restoreSettingsUiState(state) {
  if (!state) return;
  stgSegment = state.stgSegment || "system";
  stgRoleId = state.stgRoleId || "ceo";
  stgNewRoleOpen = !!state.stgNewRoleOpen;
  stgOrchestrationOpen = !!state.stgOrchestrationOpen;
  stgFounderPreviewOn = !!state.stgFounderPreviewOn;
  stgProfilePreviewOn = !!state.stgProfilePreviewOn;
}

function getRoleShort(roleId) {
  const fromPres = (data?.presentation?.roles || []).find((r) => r.id === roleId);
  if (fromPres?.short) return fromPres.short;
  const fromReg = stgRegistry.find((r) => r.id === roleId);
  if (fromReg?.shortLabel) return fromReg.shortLabel;
  return typeof ROLE_SHORT !== "undefined" ? ROLE_SHORT[roleId] || roleId : roleId;
}

function stgAvatarSrc(roleId, avatar) {
  if (avatar && avatar.startsWith("/")) return avatar;
  if (avatar && avatar.startsWith("http")) return avatar;
  return `../../assets/avatars/${roleId}.png`;
}

function stgEscape(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

async function loadSettingsView() {
  try {
    stgRoleConfigs = await loadRoleConfigs();
  } catch (_) {
    stgRoleConfigs = data?.roleConfig || [];
  }
  try {
    stgRegistry = (await apiGet("/roles/registry")).data || [];
  } catch (_) {
    stgRegistry = data?.presentation?.roles || [];
  }
  try {
    stgRuntimeSettings = (await apiGet("/runtime/settings")).data;
  } catch (_) {
    stgRuntimeSettings = data?.systemSettings?.orchestration || data?.meta?.runtimeSettings || null;
  }
  if (!stgRegistry.find((r) => r.id === stgRoleId) && stgRegistry.length) {
    stgRoleId = stgRegistry[0].id;
  }
  renderSettings();
}

function renderSettingsToolbar(summary) {
  const s = summary || {};
  return `
    <div class="stg-toolbar glass">
      <div class="stg-segment fin-segment">
        <button type="button" class="fin-segment-btn ${stgSegment === "system" ? "active" : ""}"
          onclick="switchStgSegment('system')">系统设置</button>
        <button type="button" class="fin-segment-btn ${stgSegment === "roles" ? "active" : ""}"
          onclick="switchStgSegment('roles')">角色设置</button>
      </div>
      <div class="stg-toolbar-chips">
        <span class="stg-chip">${s.roleCount ?? stgRegistry.length} 角色</span>
        <span class="stg-chip">${s.activeSkillCount ?? 0} Skill</span>
      </div>
    </div>`;
}

function switchStgSegment(seg) {
  stgSegment = seg;
  renderSettings();
}

function renderSettings() {
  const root = document.getElementById("settings-root");
  if (!root) return;
  const summary = {
    roleCount: stgRegistry.length,
    activeSkillCount: (data?.skillCatalog || []).filter((s) => s.status === "active").length,
  };
  root.innerHTML = `
    ${renderSettingsToolbar(summary)}
    <div class="stg-body">
      ${stgSegment === "system" ? renderStgSystem() : renderStgRoles()}
    </div>
    ${stgNewRoleOpen ? renderStgNewRoleModal() : ""}`;
}

function renderStgSystem() {
  const fpDoc = (data?.founderProfile?.document || "").trim() || founderProfileDefaultDocument(data?.founderProfile);
  const pending = (data?.profileSuggestions || []).filter((s) => s.status === "pending").length;
  const rt = stgRuntimeSettings || {};
  const pulse = rt.pulse || {};
  const agency = rt.agency || {};
  const auto = rt.ceoAutoDispatch || {};
  const founder = rt.founderNotify || {};
  const skills = data?.skillCatalog || [];
  const mcp = data?.mcpConnections || [];

  return `
    <section class="stg-section glass">
      <div class="stg-section-head">
        <div>
          <h3>Founder Profile</h3>
          <p class="stg-hint">CEO 决策读取的协作偏好文档</p>
        </div>
        <div class="stg-section-actions">
          <button type="button" class="btn-secondary btn-sm" onclick="toggleStgFounderPreview()">预览</button>
          <button type="button" class="btn-primary btn-sm" onclick="saveStgFounderProfile()">保存</button>
        </div>
      </div>
      ${pending ? `<div class="founder-pending-hint">有 ${pending} 条偏好建议待处理 · <button type="button" class="wf-link" onclick="goToView('inbox');setInboxFilter('profile_suggestion')">去收件箱</button></div>` : ""}
      <div class="founder-doc-shell glass-inner">
        <textarea class="founder-doc-editor" id="stg-fp-document" spellcheck="false">${stgEscape(fpDoc)}</textarea>
        <div class="founder-doc-preview md-content" id="stg-fp-preview" ${stgFounderPreviewOn ? "" : "hidden"}></div>
      </div>
      <div class="settings-toast" id="stg-fp-toast"></div>
    </section>

    <section class="stg-section glass">
      <div class="stg-section-head">
        <div>
          <h3>编排与自动化</h3>
          <p class="stg-hint">Pulse 心跳 · Agency 观察 · CEO 自动派活</p>
        </div>
        <button type="button" class="btn-primary btn-sm" onclick="saveStgRuntime()">保存</button>
      </div>
      <div class="stg-orchestration-grid">
        <label class="stg-check"><input type="checkbox" id="stg-pulse" ${pulse.enabled !== false ? "checked" : ""}/> Pulse 后台心跳</label>
        <label class="stg-check"><input type="checkbox" id="stg-agency" ${agency.enabled !== false ? "checked" : ""}/> Agency 自主观察</label>
        <label class="stg-check"><input type="checkbox" id="stg-auto-dispatch" ${auto.enabled ? "checked" : ""}/> CEO 自动派活</label>
        <label class="stg-check"><input type="checkbox" id="stg-ceo-llm" ${agency.ceoDeliberateUseLlm ? "checked" : ""}/> CEO Deliberate 使用 LLM</label>
      </div>
      <details class="stg-details" ${stgOrchestrationOpen ? "open" : ""} ontoggle="stgOrchestrationOpen=this.open">
        <summary>高级参数</summary>
        <div class="settings-fields runtime-settings-grid">
          <div class="settings-field">
            <label for="stg-exec-interval">任务执行间隔（秒）</label>
            <input id="stg-exec-interval" type="number" min="2" max="120" value="${pulse.executionIntervalSec ?? 5}"/>
          </div>
          <div class="settings-field">
            <label for="stg-stale-min">Running 超时（分钟）</label>
            <input id="stg-stale-min" type="number" min="5" max="240" value="${pulse.runningStaleMin ?? 30}"/>
          </div>
          <div class="settings-field">
            <label for="stg-auto-score">自动派活 · 最低交付分</label>
            <input id="stg-auto-score" type="number" min="0" max="100" value="${auto.minDeliveryScore ?? 80}"/>
          </div>
          <div class="settings-field">
            <label for="stg-founder-cooldown">Founder 问询冷却（小时）</label>
            <input id="stg-founder-cooldown" type="number" min="1" max="168" value="${founder.openQuestionCooldownHours ?? 24}"/>
          </div>
        </div>
      </details>
      <div class="settings-toast" id="stg-rt-toast"></div>
    </section>

    <section class="stg-section glass">
      <div class="stg-section-head">
        <div><h3>Skill Hub</h3><p class="stg-hint">${skills.filter((s) => s.status === "active").length} 活跃 / ${skills.length} 总计</p></div>
        <button type="button" class="btn-secondary btn-sm" onclick="openStgSkillImport()">导入</button>
      </div>
      <div class="stg-skill-list">
        ${skills.slice(0, 20).map((s) => `
          <div class="stg-skill-row">
            <div>
              <span class="stg-skill-name">${stgEscape(s.name)}</span>
              <span class="stg-skill-meta">${s.id} · v${s.version || "1"} · ${s.status}</span>
            </div>
            <span class="stg-cap-tag">${(s.category || "—")}</span>
          </div>`).join("") || '<p class="stg-empty-hint">暂无 Skill</p>'}
      </div>
      ${stgSkillImportOpen ? renderStgSkillImportModal() : ""}
    </section>

    <section class="stg-section glass">
      <div class="stg-section-head">
        <div><h3>MCP 连接</h3><p class="stg-hint">${mcp.length} 个连接</p></div>
        <button type="button" class="btn-secondary btn-sm" onclick="openStgMcpModal()">添加</button>
      </div>
      <div class="stg-skill-list">
        ${mcp.map((c) => `
          <div class="stg-skill-row">
            <span class="stg-skill-name">${stgEscape(c.label || c.id)}</span>
            <span class="stg-skill-meta">${c.health || "unknown"} · ${(c.capabilities || []).join(", ")}</span>
          </div>`).join("") || '<p class="stg-empty-hint">尚未配置 MCP · Epic 4 可添加 stdio 连接</p>'}
      </div>
      ${stgMcpOpen ? renderStgMcpModal() : ""}
    </section>

    <section class="stg-section glass">
      <div class="stg-section-head"><div><h3>渠道</h3></div></div>
      <div class="channel-bar">
        <div class="channel-pill ${data?.channels?.feishu?.connected ? "on" : ""}">${data?.channels?.feishu?.label || "飞书"}</div>
        <div class="channel-pill ${data?.channels?.wechat?.connected ? "on" : ""}">${data?.channels?.wechat?.label || "微信"}</div>
      </div>
    </section>`;
}

function renderStgRoles() {
  const list = stgRegistry
    .map((entry) => {
      const cfg = stgRoleConfigs.find((c) => c.roleId === entry.id) || {};
      const hasKey = cfg.apiKeyConfigured || Boolean(cfg.apiKey);
      const caps = (entry.capabilities || ["text"]).map((c) => `<span class="stg-cap-tag">${c}</span>`).join("");
      return `
        <button type="button" class="stg-role-pill ${entry.id === stgRoleId ? "active" : ""}"
          onclick="selectStgRole('${entry.id}')">
          <img src="${stgAvatarSrc(entry.id, entry.avatar)}" alt=""/>
          <div class="stg-role-pill-text">
            <span class="name">${stgEscape(entry.name || entry.shortLabel)}</span>
            <span class="meta">${caps}</span>
          </div>
          <span class="settings-status ${hasKey ? "on" : "off"}">${hasKey ? "Key" : "—"}</span>
        </button>`;
    })
    .join("");

  const detail = stgRoleId ? renderStgRoleDetail() : renderStgRoleEmpty();

  return `
    <div class="stg-roles-layout">
      <aside class="stg-roles-sidebar glass">
        <div class="stg-roles-sidebar-head">
          <span class="stg-sidebar-title">角色</span>
          <button type="button" class="btn-primary btn-sm" onclick="openStgNewRole()">+ 新增</button>
        </div>
        <div class="stg-role-list">${list}</div>
      </aside>
      <div class="stg-role-detail glass">${detail}</div>
    </div>`;
}

function renderStgRoleEmpty() {
  return `<div class="stg-empty"><p>选择左侧角色，或新建一个 Agent 角色。</p></div>`;
}

function renderStgRoleDetail() {
  const entry = stgRegistry.find((r) => r.id === stgRoleId) || {};
  const cfg = stgRoleConfigs.find((c) => c.roleId === stgRoleId) || {};
  const role = (data?.roles || []).find((r) => r.id === stgRoleId) || entry;
  const profile = (data?.roleProfiles || {})[stgRoleId]?.document || "";
  const cost = data?.costs?.byRole?.find((x) => x.roleId === stgRoleId);
  const text = (cfg.models || {}).text || {};
  const providers = Object.keys(STG_API_PRESETS)
    .map((p) => `<option value="${p}" ${text.apiProvider === p || cfg.apiProvider === p ? "selected" : ""}>${p}</option>`)
    .join("");
  const keyHint = cfg.apiKeyConfigured ? "Key 已加密存储" : "尚未配置 Key";

  const modelSlots = ["text", "image", "video"].map((cap) => {
    const slot = (cfg.models || {})[cap] || {};
    const disabled = cap !== "text";
    const label = cap === "text" ? "文本对话" : cap === "image" ? "图像生成" : "视频生成";
    return `
      <div class="stg-model-slot ${disabled ? "disabled" : ""}">
        <div class="stg-model-slot-head">
          <span>${label}</span>
          ${disabled ? '<span class="stg-lock-hint">Epic 4 · 需 MCP</span>' : ""}
        </div>
        <div class="stg-model-slot-fields">
          <select id="stg-provider-${cap}" ${disabled ? "disabled" : ""} onchange="onStgProviderChange('${cap}')">${providers}</select>
          <input id="stg-model-${cap}" value="${stgEscape(slot.model || (cap === "text" ? cfg.model : ""))}" placeholder="模型 ID" ${disabled ? "disabled" : ""}/>
        </div>
      </div>`;
  }).join("");

  return `
    <div class="stg-detail-head">
      <img src="${stgAvatarSrc(stgRoleId, role.avatar)}" alt=""/>
      <div>
        <h3>${stgEscape(role.name || entry.name)} · ${getRoleShort(stgRoleId)}</h3>
        <p class="stg-hint">${stgEscape(role.title || entry.title || "")} · 本月 ¥${cost?.cost || 0}</p>
      </div>
    </div>

    <div class="stg-detail-section">
      <div class="stg-detail-label">身份</div>
      <div class="stg-identity-grid">
        <div class="settings-field"><label>姓名</label><input id="stg-id-name" value="${stgEscape(role.name || "")}"/></div>
        <div class="settings-field"><label>职位</label><input id="stg-id-title" value="${stgEscape(role.title || "")}"/></div>
        <div class="settings-field"><label>部门</label><input id="stg-id-dept" value="${stgEscape(role.department || entry.department || "")}"/></div>
        <div class="settings-field stg-full"><label>Charter</label><input id="stg-id-charter" value="${stgEscape(role.charter || "")}"/></div>
      </div>
      <button type="button" class="btn-secondary btn-sm" onclick="saveStgIdentity()">保存身份</button>
    </div>

    <div class="stg-detail-section">
      <div class="stg-detail-label">Profile</div>
      <div class="founder-doc-shell">
        <textarea class="founder-doc-editor stg-role-profile" id="stg-role-profile" spellcheck="false">${stgEscape(profile)}</textarea>
        <div class="founder-doc-preview md-content" id="stg-role-profile-preview" ${stgProfilePreviewOn ? "" : "hidden"}></div>
      </div>
      <div class="stg-inline-actions">
        <button type="button" class="btn-secondary btn-sm" onclick="toggleStgProfilePreview()">预览</button>
        <button type="button" class="btn-secondary btn-sm" onclick="saveStgProfile()">保存 Profile</button>
      </div>
    </div>

    <div class="stg-detail-section">
      <div class="stg-detail-label">模型槽</div>
      ${modelSlots}
      <div class="settings-field"><label for="stg-url">API Base URL</label>
        <input id="stg-url" value="${stgEscape(text.apiBaseUrl || cfg.apiBaseUrl || STG_API_PRESETS.OpenRouter)}"/></div>
      <div class="settings-field"><label for="stg-key">API Key</label>
        <input id="stg-key" type="password" autocomplete="off" placeholder="留空则不修改"/>
        <div class="hint">${keyHint}</div></div>
      <div class="settings-field"><label for="stg-budget">月预算（CNY）</label>
        <input id="stg-budget" type="number" min="0" value="${cfg.monthlyBudget || 0}"/></div>
    </div>

    <div class="stg-detail-section">
      <div class="stg-detail-label">技能</div>
      <div class="stg-cap-grid">
        ${(data?.skillCatalog || []).filter((s) => s.status === "active").map((s) => {
          const checked = (cfg.enabledSkills || []).includes(s.id);
          return `<label class="stg-check"><input type="checkbox" name="stg-skill" value="${s.id}" ${checked ? "checked" : ""}/> ${stgEscape(s.name)}</label>`;
        }).join("") || '<p class="stg-empty-hint">Hub 中暂无 active Skill</p>'}
      </div>
    </div>

    <div class="settings-actions">
      <button type="button" class="btn-primary" onclick="saveStgRoleConfig()">保存配置</button>
      <button type="button" class="btn-secondary" onclick="testStgConnection()">测试连接</button>
    </div>
    <div class="settings-toast" id="stg-config-toast"></div>`;
}

function renderStgNewRoleModal() {
  const capChecks = STG_CAPABILITIES.map(
    (c) => `<label class="stg-check"><input type="checkbox" name="stg-new-cap" value="${c.id}" ${c.id === "text" ? "checked" : ""}/> ${c.label}</label>`
  ).join("");
  return `
    <div class="stg-modal open" onclick="if(event.target===this)closeStgNewRole()">
      <div class="stg-modal-panel glass" role="dialog">
        <div class="stg-modal-head">
          <h3>新增角色</h3>
          <button type="button" class="modal-close" onclick="closeStgNewRole()">×</button>
        </div>
        <div class="settings-fields">
          <div class="settings-field"><label>角色 ID *</label>
            <input id="stg-new-id" placeholder="brand · 小写英文"/></div>
          <div class="settings-field"><label>显示名 *</label>
            <input id="stg-new-name" placeholder="苏见"/></div>
          <div class="settings-field"><label>职位</label>
            <input id="stg-new-title" placeholder="品牌设计 · AI"/></div>
          <div class="settings-field"><label>部门</label>
            <input id="stg-new-dept" placeholder="品牌部"/></div>
          <div class="settings-field"><label>能力 *</label>
            <div class="stg-cap-grid">${capChecks}</div></div>
          <label class="stg-check"><input type="checkbox" id="stg-new-dispatch" checked/> CEO 可派活</label>
        </div>
        <div class="settings-actions">
          <button type="button" class="btn-primary" onclick="submitStgNewRole()">创建</button>
          <button type="button" class="btn-secondary" onclick="closeStgNewRole()">取消</button>
        </div>
        <div class="settings-toast" id="stg-new-toast"></div>
      </div>
    </div>`;
}

function selectStgRole(id) {
  stgRoleId = id;
  stgProfilePreviewOn = false;
  renderSettings();
}

function openStgNewRole() {
  stgNewRoleOpen = true;
  renderSettings();
}

function closeStgNewRole() {
  stgNewRoleOpen = false;
  renderSettings();
}

async function submitStgNewRole() {
  const toast = document.getElementById("stg-new-toast");
  const id = document.getElementById("stg-new-id")?.value?.trim().toLowerCase();
  const name = document.getElementById("stg-new-name")?.value?.trim();
  const caps = [...document.querySelectorAll('input[name="stg-new-cap"]:checked')].map((el) => el.value);
  if (!id || !name || !caps.length) {
    if (toast) toast.textContent = "请填写 ID、显示名并选择能力";
    return;
  }
  try {
    await apiPost("/roles/registry", {
      id,
      name,
      title: document.getElementById("stg-new-title")?.value?.trim() || "",
      department: document.getElementById("stg-new-dept")?.value?.trim() || "",
      capabilities: caps,
      dispatchable: document.getElementById("stg-new-dispatch")?.checked ?? true,
      shortLabel: name.slice(0, 2),
    });
    stgNewRoleOpen = false;
    stgRoleId = id;
    await refreshDashboard();
    await loadSettingsView();
    if (toast) toast.textContent = "✓ 角色已创建";
  } catch (e) {
    if (toast) toast.textContent = `创建失败：${e.message}`;
  }
}

function onStgProviderChange(cap) {
  const provider = document.getElementById(`stg-provider-${cap}`)?.value;
  const urlInput = document.getElementById("stg-url");
  if (!urlInput || !provider || provider === "Custom") return;
  const preset = STG_API_PRESETS[provider];
  if (preset) urlInput.value = preset;
}

function toggleStgFounderPreview() {
  stgFounderPreviewOn = !stgFounderPreviewOn;
  const editor = document.getElementById("stg-fp-document");
  const preview = document.getElementById("stg-fp-preview");
  if (!editor || !preview) return;
  if (stgFounderPreviewOn) {
    preview.innerHTML = simpleMarkdown(editor.value || "");
    preview.hidden = false;
    editor.hidden = true;
  } else {
    preview.hidden = true;
    editor.hidden = false;
  }
}

function toggleStgProfilePreview() {
  stgProfilePreviewOn = !stgProfilePreviewOn;
  const editor = document.getElementById("stg-role-profile");
  const preview = document.getElementById("stg-role-profile-preview");
  if (!editor || !preview) return;
  if (stgProfilePreviewOn) {
    preview.innerHTML = simpleMarkdown(editor.value || "");
    preview.hidden = false;
    editor.hidden = true;
  } else {
    preview.hidden = true;
    editor.hidden = false;
  }
}

async function saveStgFounderProfile() {
  const toast = document.getElementById("stg-fp-toast");
  const documentText = document.getElementById("stg-fp-document")?.value ?? "";
  if (!documentText.trim()) {
    if (toast) toast.textContent = "文档不能为空";
    return;
  }
  try {
    const res = await apiPut("/founder/profile", { document: documentText });
    data.founderProfile = res.data;
    stgFounderPreviewOn = false;
    if (toast) toast.textContent = "✓ Founder Profile 已保存";
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function saveStgRuntime() {
  const toast = document.getElementById("stg-rt-toast");
  const body = {
    pulse: {
      enabled: document.getElementById("stg-pulse")?.checked ?? true,
      executionIntervalSec: Number(document.getElementById("stg-exec-interval")?.value || 5),
      runningStaleMin: Number(document.getElementById("stg-stale-min")?.value || 30),
    },
    agency: {
      enabled: document.getElementById("stg-agency")?.checked ?? true,
      ceoDeliberateUseLlm: document.getElementById("stg-ceo-llm")?.checked ?? false,
    },
    ceoAutoDispatch: {
      enabled: document.getElementById("stg-auto-dispatch")?.checked ?? false,
      minDeliveryScore: Number(document.getElementById("stg-auto-score")?.value || 80),
    },
    founderNotify: {
      openQuestionCooldownHours: Number(document.getElementById("stg-founder-cooldown")?.value || 24),
    },
  };
  try {
    const res = await apiPatch("/system/settings", { orchestration: body });
    stgRuntimeSettings = res.data?.orchestration || res.data;
    if (toast) toast.textContent = "✓ 编排配置已保存";
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function saveStgIdentity() {
  const toast = document.getElementById("stg-config-toast");
  try {
    await apiPatch(`/roles/${stgRoleId}/identity`, {
      name: document.getElementById("stg-id-name")?.value?.trim(),
      title: document.getElementById("stg-id-title")?.value?.trim(),
      department: document.getElementById("stg-id-dept")?.value?.trim(),
      charter: document.getElementById("stg-id-charter")?.value?.trim(),
    });
    await refreshDashboard();
    stgRegistry = (await apiGet("/roles/registry")).data || stgRegistry;
    if (toast) toast.textContent = "✓ 身份已保存";
    renderSettings();
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function saveStgProfile() {
  const toast = document.getElementById("stg-config-toast");
  const doc = document.getElementById("stg-role-profile")?.value ?? "";
  try {
    await apiPut(`/roles/${stgRoleId}/profile`, { document: doc });
    if (!data.roleProfiles) data.roleProfiles = {};
    data.roleProfiles[stgRoleId] = { document: doc };
    stgProfilePreviewOn = false;
    if (toast) toast.textContent = "✓ Profile 已保存";
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function saveStgRoleConfig() {
  const toast = document.getElementById("stg-config-toast");
  const enabledSkills = [...document.querySelectorAll('input[name="stg-skill"]:checked')].map((el) => el.value);
  const body = {
    models: {
      text: {
        model: document.getElementById("stg-model-text")?.value?.trim(),
        apiProvider: document.getElementById("stg-provider-text")?.value,
        apiBaseUrl: document.getElementById("stg-url")?.value?.trim(),
      },
    },
    monthlyBudget: Number(document.getElementById("stg-budget")?.value || 0),
    enabledSkills,
  };
  const key = document.getElementById("stg-key")?.value?.trim();
  if (key) body.apiKey = key;
  try {
    const res = await apiPut(`/roles/config/${stgRoleId}`, body);
    const idx = stgRoleConfigs.findIndex((c) => c.roleId === stgRoleId);
    if (idx >= 0) stgRoleConfigs[idx] = res.data;
    await refreshDashboard();
    if (toast) toast.textContent = "✓ 配置已保存";
    const keyEl = document.getElementById("stg-key");
    if (keyEl) keyEl.value = "";
    renderSettings();
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function testStgConnection() {
  const toast = document.getElementById("stg-config-toast");
  if (toast) toast.textContent = "正在测试…";
  try {
    await saveStgRoleConfig();
    const body = {
      model: document.getElementById("stg-model-text")?.value?.trim(),
      apiProvider: document.getElementById("stg-provider-text")?.value,
      apiBaseUrl: document.getElementById("stg-url")?.value?.trim(),
      capability: "text",
    };
    const res = await apiPost(`/roles/config/${stgRoleId}/test`, body);
    if (toast) toast.textContent = `✓ 连接成功 · ${res.data.model}`;
  } catch (e) {
    if (toast) toast.textContent = `测试失败：${e.message}`;
  }
}

function openStgSkillImport() {
  stgSkillImportOpen = true;
  renderSettings();
}

function closeStgSkillImport() {
  stgSkillImportOpen = false;
  renderSettings();
}

function renderStgSkillImportModal() {
  return `
    <div class="stg-modal open" onclick="if(event.target===this)closeStgSkillImport()">
      <div class="stg-modal-panel glass">
        <div class="stg-modal-head"><h3>导入 SKILL.md</h3><button type="button" class="modal-close" onclick="closeStgSkillImport()">×</button></div>
        <textarea class="founder-doc-editor" id="stg-skill-md" spellcheck="false" placeholder="---\\nid: my_skill\\n..."></textarea>
        <div class="settings-actions">
          <button type="button" class="btn-primary" onclick="submitStgSkillImport()">导入</button>
        </div>
        <div class="settings-toast" id="stg-skill-import-toast"></div>
      </div>
    </div>`;
}

async function submitStgSkillImport() {
  const toast = document.getElementById("stg-skill-import-toast");
  const md = document.getElementById("stg-skill-md")?.value ?? "";
  try {
    await apiPost("/skills/import", { markdown: md });
    stgSkillImportOpen = false;
    await refreshDashboard();
    renderSettings();
    if (toast) toast.textContent = "✓ 已导入";
  } catch (e) {
    if (toast) toast.textContent = `导入失败：${e.message}`;
  }
}

function openStgMcpModal() {
  stgMcpOpen = true;
  renderSettings();
}

function closeStgMcpModal() {
  stgMcpOpen = false;
  renderSettings();
}

function renderStgMcpModal() {
  return `
    <div class="stg-modal open" onclick="if(event.target===this)closeStgMcpModal()">
      <div class="stg-modal-panel glass">
        <div class="stg-modal-head"><h3>添加 MCP 连接</h3><button type="button" class="modal-close" onclick="closeStgMcpModal()">×</button></div>
        <div class="settings-fields">
          <div class="settings-field"><label>ID</label><input id="stg-mcp-id" placeholder="image_gen_local"/></div>
          <div class="settings-field"><label>名称</label><input id="stg-mcp-label" placeholder="本地图像 MCP"/></div>
        </div>
        <div class="settings-actions"><button type="button" class="btn-primary" onclick="submitStgMcp()">添加</button></div>
        <div class="settings-toast" id="stg-mcp-toast"></div>
      </div>
    </div>`;
}

async function submitStgMcp() {
  const toast = document.getElementById("stg-mcp-toast");
  try {
    await apiPost("/mcp/connections", {
      id: document.getElementById("stg-mcp-id")?.value?.trim(),
      label: document.getElementById("stg-mcp-label")?.value?.trim(),
      capabilities: ["image"],
      allowedRoles: [],
    });
    stgMcpOpen = false;
    await refreshDashboard();
    renderSettings();
  } catch (e) {
    if (toast) toast.textContent = `失败：${e.message}`;
  }
}

window.renderSettings = renderSettings;
window.loadSettingsView = loadSettingsView;
window.isSettingsUiInteractive = isSettingsUiInteractive;
window.captureSettingsUiState = captureSettingsUiState;
window.restoreSettingsUiState = restoreSettingsUiState;
window.getRoleShort = getRoleShort;
window.switchStgSegment = switchStgSegment;
window.selectStgRole = selectStgRole;
window.openStgNewRole = openStgNewRole;
window.closeStgNewRole = closeStgNewRole;
window.submitStgNewRole = submitStgNewRole;
window.onStgProviderChange = onStgProviderChange;
window.toggleStgFounderPreview = toggleStgFounderPreview;
window.toggleStgProfilePreview = toggleStgProfilePreview;
window.saveStgFounderProfile = saveStgFounderProfile;
window.saveStgRuntime = saveStgRuntime;
window.saveStgIdentity = saveStgIdentity;
window.saveStgProfile = saveStgProfile;
window.saveStgRoleConfig = saveStgRoleConfig;
window.testStgConnection = testStgConnection;
window.openStgSkillImport = openStgSkillImport;
window.closeStgSkillImport = closeStgSkillImport;
window.submitStgSkillImport = submitStgSkillImport;
window.openStgMcpModal = openStgMcpModal;
window.closeStgMcpModal = closeStgMcpModal;
window.submitStgMcp = submitStgMcp;
