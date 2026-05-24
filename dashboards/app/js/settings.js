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
let stgChannelSetup = null;
let stgChannelSettings = null;
let stgChannelStatus = null;
let stgWechatDetect = null;
let stgToolRegistry = [];
let stgSkillRoutes = {};
let stgSkillChains = [];
let stgSkillSearch = "";
let stgSkillDrawerId = null;

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

function isSettingsViewActive() {
  return typeof getActiveViewId === "function" && getActiveViewId() === "settings";
}

function isSettingsUiInteractive() {
  if (!isSettingsViewActive()) return false;
  if (stgNewRoleOpen || stgSkillImportOpen || stgMcpOpen) return true;
  const root = document.getElementById("settings-root");
  if (!root) return false;
  const active = document.activeElement;
  if (active && active !== document.body && root.contains(active)) return true;
  if (root.querySelector(".stg-modal.open, details[open]")) return true;
  if (stgFounderPreviewOn || stgProfilePreviewOn) return true;
  return false;
}

function captureSettingsFormDraft() {
  const root = document.getElementById("settings-root");
  if (!root) return null;
  const draft = { roleId: stgRoleId, segment: stgSegment, fields: {}, checks: {}, textareas: {} };
  root.querySelectorAll("input[id], select[id], textarea[id]").forEach((el) => {
    if (!el.id) return;
    if (el.type === "checkbox") draft.checks[el.id] = el.checked;
    else if (el.tagName === "TEXTAREA") draft.textareas[el.id] = el.value;
    else draft.fields[el.id] = el.value;
  });
  return draft;
}

function restoreSettingsFormDraft(draft) {
  if (!draft || draft.roleId !== stgRoleId || draft.segment !== stgSegment) return;
  const root = document.getElementById("settings-root");
  if (!root) return;
  Object.entries(draft.fields || {}).forEach(([id, val]) => {
    const el = root.querySelector(`#${CSS.escape(id)}`);
    if (el && el.type !== "checkbox") el.value = val;
  });
  Object.entries(draft.textareas || {}).forEach(([id, val]) => {
    const el = root.querySelector(`#${CSS.escape(id)}`);
    if (el) el.value = val;
  });
  Object.entries(draft.checks || {}).forEach(([id, val]) => {
    const el = root.querySelector(`#${CSS.escape(id)}`);
    if (el) el.checked = val;
  });
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
  if (avatar && (avatar.startsWith("http://") || avatar.startsWith("https://") || avatar.startsWith("/"))) {
    return avatar;
  }
  return `/assets/avatars/${roleId}.png`;
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
  try {
    stgChannelSetup = (await apiGet("/channels/setup")).data;
  } catch (_) {
    stgChannelSetup = null;
  }
  try {
    stgChannelSettings = (await apiGet("/system/settings")).data?.channels || null;
  } catch (_) {
    stgChannelSettings = data?.systemSettings?.channels || null;
  }
  try {
    stgChannelStatus = (await apiGet("/channels/status")).data;
  } catch (_) {
    stgChannelStatus = data?.channels || null;
  }
  try {
    stgWechatDetect = (await apiGet("/channels/wechat/detect")).data;
  } catch (_) {
    stgWechatDetect = null;
  }
  try {
    stgToolRegistry = (await apiGet("/tools")).data || [];
  } catch (_) {
    stgToolRegistry = [];
  }
  try {
    stgSkillRoutes = (await apiGet("/meta/skill-routes")).data || {};
  } catch (_) {
    stgSkillRoutes = data?.meta?.skillRoutes || {};
  }
  try {
    stgSkillChains = (await apiGet("/skill-chains")).data || [];
  } catch (_) {
    stgSkillChains = data?.skillChains || [];
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
  const draft = isSettingsUiInteractive() ? captureSettingsFormDraft() : null;
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
  if (draft) restoreSettingsFormDraft(draft);
  if (stgFounderPreviewOn) toggleStgFounderPreview();
  if (stgProfilePreviewOn) toggleStgProfilePreview();
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
        <label class="stg-check"><input type="checkbox" id="stg-role-llm" ${agency.roleDeliberateUseLlm ? "checked" : ""}/> 角色 Proposal 使用 LLM</label>
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
          <div class="settings-field">
            <label for="stg-proposal-max">Proposal 日上限</label>
            <input id="stg-proposal-max" type="number" min="1" max="100" value="${founder.maxProposalsPerDay ?? 10}"/>
          </div>
          <label class="stg-check stg-full"><input type="checkbox" id="stg-pause-ceo-thread" ${agency.pauseWhileCeoThreadPending !== false ? "checked" : ""}/> CEO 对话时暂停 Agency</label>
        </div>
      </details>
      <div class="settings-toast" id="stg-rt-toast"></div>
    </section>

    <section class="stg-section glass">
      <div class="stg-section-head">
        <div><h3>Skill Hub</h3><p class="stg-hint">${skills.filter((s) => s.status === "active").length} 活跃 / ${skills.length} 总计</p></div>
        <button type="button" class="btn-secondary btn-sm" onclick="openStgSkillImport()">导入</button>
      </div>
      <div class="settings-field stg-full">
        <input id="stg-skill-search" type="search" placeholder="搜索 Skill…" value="${stgEscape(stgSkillSearch)}" oninput="onStgSkillSearch(this.value)"/>
      </div>
      <div class="stg-skill-list">
        ${renderStgSkillListRows(skills)}
      </div>
      ${stgSkillDrawerId ? renderStgSkillDrawer() : ""}
      ${stgSkillImportOpen ? renderStgSkillImportModal() : ""}
    </section>

    <section class="stg-section glass">
      <div class="stg-section-head">
        <div><h3>Skill 路由</h3><p class="stg-hint">taskKind → skillId</p></div>
        <button type="button" class="btn-secondary btn-sm" onclick="saveStgSkillRoutes()">保存路由</button>
      </div>
      <div class="stg-form-grid" id="stg-skill-routes">
        ${renderStgSkillRouteRows()}
      </div>
      <div class="settings-toast" id="stg-routes-toast"></div>
    </section>

    <section class="stg-section glass">
      <div class="stg-section-head">
        <div><h3>Skill 链</h3><p class="stg-hint">${stgSkillChains.length} 条链 · CEO 派活可选</p></div>
        <button type="button" class="btn-secondary btn-sm" onclick="openStgChainEditor()">新建链</button>
      </div>
      <div class="stg-skill-list">
        ${stgSkillChains.map((c) => `
          <div class="stg-skill-row">
            <div>
              <span class="stg-skill-name">${stgEscape(c.name || c.id)}</span>
              <span class="stg-skill-meta">${c.id} · ${(c.steps || []).length} 步</span>
            </div>
          </div>`).join("") || '<p class="stg-empty-hint">尚未创建 Skill 链</p>'}
      </div>
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
      <div class="stg-section-head"><div><h3>渠道</h3><p class="stg-hint">微信 ClawBot · 飞书 Bot · Web CEO</p></div></div>
      ${renderStgChannels()}
    </section>`;
}

function renderStgChannels() {
  const setup = stgChannelSetup || {};
  const claw = setup.wechat?.clawbot || {};
  const bridge = setup.wechat?.opcBridge || {};
  const steps = claw.steps || [];
  const detect = stgWechatDetect || {};
  const feishu = setup.feishu || {};
  const wc = stgChannelSettings?.wechat || {};
  const wcStatus = stgChannelStatus?.wechat || data?.channels?.wechat || {};
  const feishuOn = stgChannelStatus?.feishu?.connected || data?.channels?.feishu?.connected;
  const wechatOn = wcStatus.connected;
  const outMode = wc.outboundMode || "openclaw";
  const gwMasked = typeof wc.gatewayToken === "object" ? wc.gatewayToken?.masked : "";
  const gwDefault = wc.gatewayUrl || detect.suggestedGatewayUrls?.[0] || "";
  const feishuWebhook = feishu.webhookUrl || `${typeof window !== "undefined" ? window.location.origin : ""}/api/v1/channels/feishu/webhook`;
  const openclawHint = detect.openclawInstalled
    ? `已检测到 OpenClaw${detect.openclawVersion ? ` ${detect.openclawVersion}` : ""}`
    : "未检测到 openclaw CLI — 运行下方命令时会自动安装插件";
  const stepList = steps.length ? steps : [
    { title: "终端安装并扫码", detail: claw.summary, command: claw.cli },
    { title: "或在手机微信", detail: claw.wechatEntry },
    { title: "连接 OPC CEO", detail: "启动 Bridge 将微信消息转发至 CEO", command: bridge.bridgeStart },
  ];
  const stepHtml = stepList.map((step, i) => `
    <div class="stg-wx-step">
      <span class="stg-wx-step-num">${i + 1}</span>
      <div class="stg-wx-step-body">
        <strong>${stgEscape(step.title || `步骤 ${i + 1}`)}</strong>
        ${step.detail ? `<p class="stg-hint stg-hint--tight">${stgEscape(step.detail)}</p>` : ""}
        ${step.command ? `<code class="stg-code stg-cli">${stgEscape(step.command)}</code>` : ""}
      </div>
    </div>`).join("");
  return `
    <div class="stg-channel-grid stg-channel-grid--compact">
      <div class="stg-channel-card glass-inner stg-wx-card">
        <div class="stg-channel-head">
          <span class="stg-channel-title">微信 · ClawBot</span>
          <span class="channel-pill ${wechatOn ? "on" : ""}">${wechatOn ? "已连接" : "待扫码"}</span>
        </div>
        <p class="stg-hint">${stgEscape(claw.note || "与官方一致：终端出二维码 → 微信扫码，无需先填 Gateway URL。")}</p>
        <p class="stg-hx-tag ${detect.openclawInstalled ? "ok" : ""}">${stgEscape(openclawHint)}</p>
        <div class="stg-wx-flow">${stepHtml}</div>
        <div class="stg-section-actions stg-section-actions--tight">
          <button type="button" class="btn-secondary btn-sm" onclick="copyStgClawbotCli()">复制安装命令</button>
          <button type="button" class="btn-secondary btn-sm" onclick="copyStgBridgeStart()">复制 Bridge 命令</button>
          <button type="button" class="btn-primary btn-sm" onclick="testStgWechatChannels()">检测 Bridge</button>
        </div>
        ${wcStatus.lastInboundAt ? `<p class="stg-hint stg-hint--tight">最近微信入站 ${stgEscape(wcStatus.lastInboundAt)}</p>` : ""}
        <details class="stg-channel-more">
          <summary>高级：Bridge Gateway（仅 Bridge 连不上时用）</summary>
          <p class="stg-hint stg-hint--tight">官方 ClawBot 扫码后由 OpenClaw 管理微信；此处仅配置 OPC Bridge 访问 Gateway 的地址。</p>
          <div class="stg-form-stack">
            <label class="stg-field"><span>Gateway URL</span>
              <input type="url" id="stg-wx-gateway" value="${stgEscape(gwDefault)}" placeholder="http://127.0.0.1:9200"/>
            </label>
            <label class="stg-field"><span>Gateway Token</span>
              <input type="password" id="stg-wx-token" placeholder="${gwMasked ? stgEscape(gwMasked) : "OpenClaw Gateway token（可选）"}"/>
            </label>
            <div class="stg-form-grid stg-form-grid--inline">
              <label class="stg-field"><span>出站模式</span>
                <select id="stg-wx-out-mode">
                  <option value="openclaw" ${outMode === "openclaw" ? "selected" : ""}>OpenClaw</option>
                  <option value="webhook" ${outMode === "webhook" ? "selected" : ""}>Webhook</option>
                </select>
              </label>
              <label class="stg-field"><span>Webhook URL</span>
                <input type="url" id="stg-wx-webhook" value="${stgEscape(wc.webhookUrl || "")}" placeholder="仅社区 gateway 用"/>
              </label>
            </div>
          </div>
          <div class="stg-section-actions stg-section-actions--tight">
            <button type="button" class="btn-secondary btn-sm" onclick="saveStgWechatChannels()">保存高级配置</button>
          </div>
        </details>
      </div>
      <div class="stg-channel-card glass-inner">
        <div class="stg-channel-head">
          <span class="stg-channel-title">飞书</span>
          <span class="channel-pill ${feishuOn ? "on" : ""}">${feishuOn ? "已连接" : "待配置"}</span>
        </div>
        <div class="stg-form-stack">
          <label class="stg-field"><span>App ID</span>
            <input type="text" id="stg-fs-appid" value="${stgEscape((stgChannelSettings?.feishu || {}).appId || "")}" placeholder="cli_xxx"/>
          </label>
          <label class="stg-field"><span>App Secret</span>
            <input type="password" id="stg-fs-secret" placeholder="留空则不修改"/>
          </label>
          <label class="stg-field"><span>Verification Token</span>
            <input type="password" id="stg-fs-token" placeholder="事件订阅验签"/>
          </label>
          <div class="stg-webhook-block">
            <span class="stg-webhook-label">Webhook</span>
            <code class="stg-code stg-webhook-url">${stgEscape(feishuWebhook)}</code>
          </div>
        </div>
        <div class="stg-section-actions stg-section-actions--tight">
          <button type="button" class="btn-primary btn-sm" onclick="saveStgFeishuChannels()">保存</button>
        </div>
      </div>
    </div>
    <div class="settings-toast" id="stg-channel-toast"></div>`;
}

async function saveStgWechatChannels() {
  const toast = document.getElementById("stg-channel-toast");
  const patch = {
    wechat: {
      enabled: true,
      outboundEnabled: true,
      outboundMode: document.getElementById("stg-wx-out-mode")?.value || "openclaw",
      gatewayUrl: document.getElementById("stg-wx-gateway")?.value?.trim() || "",
      webhookUrl: document.getElementById("stg-wx-webhook")?.value?.trim() || "",
    },
  };
  const token = document.getElementById("stg-wx-token")?.value?.trim();
  if (token) patch.wechat.gatewayToken = token;
  try {
    const res = await apiPatch("/system/settings", { channels: patch });
    stgChannelSettings = res.data?.channels || stgChannelSettings;
    if (toast) toast.textContent = "✓ 微信渠道配置已保存";
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function testStgWechatChannels() {
  const toast = document.getElementById("stg-channel-toast");
  try {
    const res = await apiPost("/channels/wechat/test", { text: "OPC Studio 渠道测试 ✓" });
    const probe = res.data?.probe || {};
    const send = res.data?.send;
    if (probe.ok) {
      if (toast) toast.textContent = send?.ok ? "✓ Bridge Gateway 可达且测试消息已发送" : "✓ Bridge Gateway 可达（微信扫码后启动 Bridge 即可收消息）";
    } else {
      if (toast) toast.textContent = `Bridge 未连通：${probe.detail || "请先运行 ClawBot 安装命令扫码，再启动 bridge/openclaw-opc"}`;
    }
    stgChannelStatus = (await apiGet("/channels/status")).data;
    renderSettings();
  } catch (e) {
    if (toast) toast.textContent = `测试失败：${e.message}`;
  }
}

function copyStgText(text) {
  if (!text) return;
  const toast = document.getElementById("stg-channel-toast");
  navigator.clipboard?.writeText(text).then(() => {
    if (toast) toast.textContent = "✓ 已复制";
  }).catch(() => {
    if (toast) toast.textContent = text;
  });
}

function copyStgClawbotCli() {
  const setup = stgChannelSetup || {};
  const cmd = setup.wechat?.clawbot?.cli || stgWechatDetect?.clawbotCli || "npx -y @tencent-weixin/openclaw-weixin-cli@latest install";
  copyStgText(cmd);
}

function copyStgBridgeStart() {
  const bridge = stgChannelSetup?.wechat?.opcBridge || {};
  copyStgText(bridge.bridgeStart || "cd bridge/openclaw-opc && npm install && npm start");
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
          <img src="${stgAvatarSrc(entry.id, entry.avatar)}" alt="" onerror="onAvatarError(this)"/>
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

function stgProviderOptions(selected) {
  return Object.keys(STG_API_PRESETS)
    .map((p) => `<option value="${p}" ${selected === p ? "selected" : ""}>${p}</option>`)
    .join("");
}

function stgRoleModelCaps(entry) {
  const caps = new Set(entry?.capabilities || ["text"]);
  caps.add("text");
  return ["text", "image", "video"].filter((c) => caps.has(c));
}

function renderStgModelSlot(cap, cfg, fallbackProvider) {
  const slot = (cfg.models || {})[cap] || {};
  const label = STG_CAPABILITIES.find((c) => c.id === cap)?.label || cap;
  const provider = slot.apiProvider || fallbackProvider || "OpenRouter";
  const url = slot.apiBaseUrl || STG_API_PRESETS[provider] || STG_API_PRESETS.OpenRouter;
  const keyPlaceholder = slot.apiKeyConfigured
    ? (slot.apiKeyMasked
      ? `已配置 · ${String(slot.apiKeyMasked).slice(0, 20)}${String(slot.apiKeyMasked).length > 20 ? "…" : ""} · 留空不修改`
      : "已配置 · 留空则不修改")
    : "输入 API Key";
  return `
    <div class="stg-model-slot" data-cap="${cap}">
      <div class="stg-model-slot-head"><span>${label}</span></div>
      <div class="stg-model-slot-fields stg-model-slot-fields--wide">
        <div class="settings-field">
          <label for="stg-provider-${cap}">Provider</label>
          <select id="stg-provider-${cap}" onchange="onStgProviderChange('${cap}')">${stgProviderOptions(provider)}</select>
        </div>
        <div class="settings-field">
          <label for="stg-model-${cap}">模型 ID</label>
          <input id="stg-model-${cap}" value="${stgEscape(slot.model || (cap === "text" ? cfg.model : ""))}" placeholder="gpt-4o-mini"/>
        </div>
        <div class="settings-field stg-full">
          <label for="stg-url-${cap}">API Base URL</label>
          <input id="stg-url-${cap}" value="${stgEscape(url)}"/>
        </div>
        <div class="settings-field stg-full">
          <label for="stg-key-${cap}">API Key</label>
          <input id="stg-key-${cap}" type="password" autocomplete="off" placeholder="${stgEscape(keyPlaceholder)}"/>
        </div>
      </div>
    </div>`;
}

function renderStgRoleDetail() {
  const entry = stgRegistry.find((r) => r.id === stgRoleId) || {};
  const cfg = stgRoleConfigs.find((c) => c.roleId === stgRoleId) || {};
  const role = (data?.roles || []).find((r) => r.id === stgRoleId) || entry;
  const profile = (data?.roleProfiles || {})[stgRoleId]?.document || "";
  const cost = data?.costs?.byRole?.find((x) => x.roleId === stgRoleId);
  const modelCaps = stgRoleModelCaps(entry);
  const modelSlots = modelCaps.map((cap) => renderStgModelSlot(cap, cfg, cfg.apiProvider)).join("");

  return `
    <div class="stg-detail-head stg-detail-head--editable">
      <div class="stg-avatar-edit">
        <img id="stg-avatar-preview" class="stg-avatar-preview stg-avatar-preview--lg" src="${stgAvatarSrc(stgRoleId, role.avatar)}" alt="" onerror="onAvatarError(this)"/>
        <label class="btn-secondary btn-sm stg-avatar-upload">
          更换头像
          <input type="file" id="stg-avatar-file" accept="image/png,image/jpeg,image/webp,image/gif" hidden onchange="uploadStgAvatar(event)"/>
        </label>
      </div>
      <div>
        <h3>${stgEscape(role.name || entry.name)} · ${getRoleShort(stgRoleId)}</h3>
        <p class="stg-hint">${stgEscape(role.title || entry.title || "")} · 本月 ¥${cost?.cost || 0}</p>
        <span class="stg-hint stg-avatar-meta">PNG / JPG / WebP · 最大 5MB</span>
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
      <div class="stg-detail-label">模型配置</div>
      <p class="stg-hint">每种能力独立配置 Provider · 模型 · Base URL · API Key（与 MCP 连接无关）</p>
      ${modelSlots}
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

    <div class="stg-detail-section">
      <div class="stg-detail-label">Tool 策略</div>
      <p class="stg-hint">Allow 为空表示继承 Skill 默认；Deny 优先生效</p>
      ${renderStgToolPolicyChips(cfg)}
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
  const urlInput = document.getElementById(`stg-url-${cap}`);
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
      roleDeliberateUseLlm: document.getElementById("stg-role-llm")?.checked ?? false,
      pauseWhileCeoThreadPending: document.getElementById("stg-pause-ceo-thread")?.checked ?? true,
    },
    ceoAutoDispatch: {
      enabled: document.getElementById("stg-auto-dispatch")?.checked ?? false,
      minDeliveryScore: Number(document.getElementById("stg-auto-score")?.value || 80),
    },
    founderNotify: {
      openQuestionCooldownHours: Number(document.getElementById("stg-founder-cooldown")?.value || 24),
      maxProposalsPerDay: Number(document.getElementById("stg-proposal-max")?.value || 10),
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

async function compressAvatarFile(file, maxDim = 512, maxBytes = 4.5 * 1024 * 1024) {
  if (file.size <= maxBytes && /jpe?g$/i.test(file.name)) return file;
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      let { width, height } = img;
      const scale = Math.min(1, maxDim / Math.max(width, height, 1));
      width = Math.max(1, Math.round(width * scale));
      height = Math.max(1, Math.round(height * scale));
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      canvas.getContext("2d").drawImage(img, 0, 0, width, height);
      const encode = (quality) => {
        canvas.toBlob((blob) => {
          if (!blob) {
            reject(new Error("无法压缩图片"));
            return;
          }
          if (blob.size > maxBytes && quality > 0.45) {
            encode(quality - 0.08);
            return;
          }
          const outName = file.name.replace(/\.\w+$/, "") + ".jpg";
          resolve(new File([blob], outName, { type: "image/jpeg" }));
        }, "image/jpeg", quality);
      };
      encode(0.88);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("无法读取图片"));
    };
    img.src = url;
  });
}

async function uploadStgAvatar(ev) {
  const file = ev.target?.files?.[0];
  if (!file || !stgRoleId) return;
  const toast = document.getElementById("stg-config-toast");
  let uploadFile = file;
  try {
    if (file.size > 1024 * 1024) uploadFile = await compressAvatarFile(file);
  } catch (e) {
    if (toast) toast.textContent = `图片处理失败：${e.message}`;
    ev.target.value = "";
    return;
  }
  const fd = new FormData();
  fd.append("file", uploadFile);
  try {
    const res = await apiPostForm(`/roles/${stgRoleId}/avatar`, fd);
    const av = res.data?.avatar;
    if (av) {
      const idx = (data.roles || []).findIndex((r) => r.id === stgRoleId);
      if (idx >= 0) data.roles[idx] = { ...data.roles[idx], avatar: av };
      const reg = stgRegistry.find((r) => r.id === stgRoleId);
      if (reg) reg.avatar = av;
      const preview = document.getElementById("stg-avatar-preview");
      if (preview) preview.src = `${av}?t=${Date.now()}`;
    }
    if (toast) toast.textContent = "✓ 头像已更新";
  } catch (e) {
    if (toast) toast.textContent = `上传失败：${e.message}`;
  }
  ev.target.value = "";
}

async function saveStgIdentity() {
  const toast = document.getElementById("stg-config-toast");
  try {
    const res = await apiPatch(`/roles/${stgRoleId}/identity`, {
      name: document.getElementById("stg-id-name")?.value?.trim(),
      title: document.getElementById("stg-id-title")?.value?.trim(),
      department: document.getElementById("stg-id-dept")?.value?.trim(),
      charter: document.getElementById("stg-id-charter")?.value?.trim(),
    });
    const role = res.data;
    const idx = (data.roles || []).findIndex((r) => r.id === stgRoleId);
    if (idx >= 0) data.roles[idx] = { ...data.roles[idx], ...role };
    stgRegistry = (await apiGet("/roles/registry")).data || stgRegistry;
    if (toast) toast.textContent = "✓ 身份已保存";
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
  const entry = stgRegistry.find((r) => r.id === stgRoleId) || {};
  const modelCaps = stgRoleModelCaps(entry);
  const models = {};
  modelCaps.forEach((cap) => {
    const slot = {
      model: document.getElementById(`stg-model-${cap}`)?.value?.trim(),
      apiProvider: document.getElementById(`stg-provider-${cap}`)?.value,
      apiBaseUrl: document.getElementById(`stg-url-${cap}`)?.value?.trim(),
    };
    const key = document.getElementById(`stg-key-${cap}`)?.value?.trim();
    if (key) slot.apiKey = key;
    models[cap] = slot;
  });
  const enabledSkills = [...document.querySelectorAll('input[name="stg-skill"]:checked')].map((el) => el.value);
  const toolPolicy = collectStgToolPolicy();
  const body = {
    models,
    monthlyBudget: Number(document.getElementById("stg-budget")?.value || 0),
    enabledSkills,
    toolPolicy,
  };
  try {
    const res = await apiPut(`/roles/config/${stgRoleId}`, body);
    const idx = stgRoleConfigs.findIndex((c) => c.roleId === stgRoleId);
    if (idx >= 0) stgRoleConfigs[idx] = res.data;
    else stgRoleConfigs.push(res.data);
    await refreshDashboard();
    if (toast) toast.textContent = "✓ 配置已保存";
    modelCaps.forEach((cap) => {
      const keyEl = document.getElementById(`stg-key-${cap}`);
      if (keyEl) keyEl.value = "";
    });
    renderSettings();
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

async function testStgConnection() {
  const toast = document.getElementById("stg-config-toast");
  const cap = "text";
  if (toast) toast.textContent = "正在测试…";
  try {
    await saveStgRoleConfig();
    const body = {
      model: document.getElementById(`stg-model-${cap}`)?.value?.trim(),
      apiProvider: document.getElementById(`stg-provider-${cap}`)?.value,
      apiBaseUrl: document.getElementById(`stg-url-${cap}`)?.value?.trim(),
      capability: cap,
    };
    const key = document.getElementById(`stg-key-${cap}`)?.value?.trim();
    if (key) body.apiKey = key;
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
          <div class="settings-field stg-full"><label>stdio 命令</label><input id="stg-mcp-cmd" placeholder="npx @modelcontextprotocol/server-everything"/></div>
          <div class="settings-field stg-full"><label>环境变量（KEY=VAL，每行一个）</label><textarea id="stg-mcp-env" rows="3" placeholder="API_KEY=sk-..."></textarea></div>
        </div>
        <div class="settings-actions"><button type="button" class="btn-primary" onclick="submitStgMcp()">添加</button></div>
        <div class="settings-toast" id="stg-mcp-toast"></div>
      </div>
    </div>`;
}

async function submitStgMcp() {
  const toast = document.getElementById("stg-mcp-toast");
  const cmdLine = document.getElementById("stg-mcp-cmd")?.value?.trim() || "";
  const command = cmdLine ? cmdLine.split(/\s+/) : [];
  const envLines = (document.getElementById("stg-mcp-env")?.value || "").split("\n").filter(Boolean);
  const env = {};
  envLines.forEach((line) => {
    const idx = line.indexOf("=");
    if (idx > 0) env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
  });
  try {
    await apiPost("/mcp/connections", {
      id: document.getElementById("stg-mcp-id")?.value?.trim(),
      label: document.getElementById("stg-mcp-label")?.value?.trim(),
      transport: "stdio",
      command,
      env: Object.keys(env).length ? env : undefined,
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

function renderStgSkillListRows(skills) {
  const q = (stgSkillSearch || "").trim().toLowerCase();
  const filtered = skills.filter((s) => {
    if (!q) return true;
    return (s.name || "").toLowerCase().includes(q) || (s.id || "").toLowerCase().includes(q);
  });
  return filtered.slice(0, 40).map((s) => `
    <div class="stg-skill-row stg-skill-row--click" onclick="openStgSkillDrawer('${s.id}')">
      <div>
        <span class="stg-skill-name">${stgEscape(s.name)}</span>
        <span class="stg-skill-meta">${s.id} · v${s.version || "1"} · ${s.status}</span>
      </div>
      <span class="stg-cap-tag">${(s.category || "—")}</span>
    </div>`).join("") || '<p class="stg-empty-hint">暂无 Skill</p>';
}

function openStgSkillDrawer(id) {
  stgSkillDrawerId = id;
  renderSettings();
}

function closeStgSkillDrawer() {
  stgSkillDrawerId = null;
  renderSettings();
}

function renderStgSkillDrawer() {
  const skill = (data?.skillCatalog || []).find((s) => s.id === stgSkillDrawerId);
  if (!skill) return "";
  const tools = (skill.tools || []).join(", ") || "—";
  return `
    <div class="stg-drawer open">
      <div class="stg-drawer-panel glass">
        <div class="stg-modal-head">
          <h3>${stgEscape(skill.name)}</h3>
          <button type="button" class="modal-close" onclick="closeStgSkillDrawer()">×</button>
        </div>
        <p class="stg-hint">${stgEscape(skill.id)} · ${skill.status} · ${skill.category || ""}</p>
        <p>${stgEscape(skill.description || "")}</p>
        <p class="stg-hint"><strong>Tools:</strong> ${stgEscape(tools)}</p>
      </div>
    </div>`;
}

function onStgSkillSearch(val) {
  stgSkillSearch = val;
  const list = document.querySelector(".stg-skill-list");
  if (list) list.innerHTML = renderStgSkillListRows(data?.skillCatalog || []);
}

function renderStgSkillRouteRows() {
  const kinds = ["nda", "prd", "contract", "brand", "ops_report"];
  const skills = data?.skillCatalog || [];
  return kinds.map((kind) => {
    const val = stgSkillRoutes[kind] || "";
    const opts = skills.map((s) => `<option value="${s.id}" ${val === s.id ? "selected" : ""}>${stgEscape(s.name)}</option>`).join("");
    return `<label class="stg-field"><span>${kind}</span><select data-route-kind="${kind}"><option value="">—</option>${opts}</select></label>`;
  }).join("");
}

async function saveStgSkillRoutes() {
  const toast = document.getElementById("stg-routes-toast");
  const routes = {};
  document.querySelectorAll("[data-route-kind]").forEach((el) => {
    const kind = el.getAttribute("data-route-kind");
    const val = el.value?.trim();
    if (kind && val) routes[kind] = val;
  });
  try {
    const res = await apiPatch("/meta/skill-routes", { skillRoutes: routes });
    stgSkillRoutes = res.data || routes;
    if (toast) toast.textContent = "✓ 路由已保存";
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

function openStgChainEditor() {
  const id = prompt("链 ID（如 nda_chain）");
  if (!id) return;
  const name = prompt("显示名称", id) || id;
  const stepsRaw = prompt("步骤 skillId，逗号分隔", "legal_nda_draft");
  const steps = (stepsRaw || "").split(",").map((s) => s.trim()).filter(Boolean).map((skillId) => ({ skillId, onFail: "halt" }));
  apiPost("/skill-chains", { id, name, steps }).then(async () => {
    stgSkillChains = (await apiGet("/skill-chains")).data || [];
    await refreshDashboard();
    renderSettings();
  }).catch((e) => alert(e.message));
}

function renderStgToolPolicyChips(cfg) {
  const policy = cfg.toolPolicy || { allow: [], deny: [] };
  const allow = new Set(policy.allow || []);
  const deny = new Set(policy.deny || []);
  const chips = (stgToolRegistry || []).map((t) => {
    const id = t.id;
    let mode = "inherit";
    if (deny.has(id)) mode = "deny";
    else if (allow.has(id)) mode = "allow";
    return `<button type="button" class="stg-tool-chip mode-${mode}" data-tool-id="${id}" onclick="cycleStgToolPolicy('${id}')">${stgEscape(t.name || id)}</button>`;
  }).join("");
  return `<div class="stg-tool-chips">${chips || '<span class="stg-hint">加载 Tool Registry…</span>'}</div>`;
}

function cycleStgToolPolicy(toolId) {
  const btn = document.querySelector(`.stg-tool-chip[data-tool-id="${CSS.escape(toolId)}"]`);
  if (!btn) return;
  const modes = ["inherit", "allow", "deny"];
  const next = modes[(modes.indexOf(btn.classList.contains("mode-allow") ? "allow" : btn.classList.contains("mode-deny") ? "deny" : "inherit") + 1) % 3];
  btn.classList.remove("mode-inherit", "mode-allow", "mode-deny");
  btn.classList.add(`mode-${next}`);
}

function collectStgToolPolicy() {
  const allow = [];
  const deny = [];
  document.querySelectorAll(".stg-tool-chip").forEach((btn) => {
    const id = btn.getAttribute("data-tool-id");
    if (!id) return;
    if (btn.classList.contains("mode-allow")) allow.push(id);
    if (btn.classList.contains("mode-deny")) deny.push(id);
  });
  return { allow, deny };
}

async function saveStgFeishuChannels() {
  const toast = document.getElementById("stg-channel-toast");
  const patch = {
    feishu: {
      enabled: true,
      appId: document.getElementById("stg-fs-appid")?.value?.trim() || "",
    },
  };
  const secret = document.getElementById("stg-fs-secret")?.value?.trim();
  const token = document.getElementById("stg-fs-token")?.value?.trim();
  if (secret) patch.feishu.appSecret = secret;
  if (token) patch.feishu.verificationToken = token;
  try {
    const res = await apiPatch("/system/settings", { channels: patch });
    stgChannelSettings = res.data?.channels || stgChannelSettings;
    if (toast) toast.textContent = "✓ 飞书配置已保存";
  } catch (e) {
    if (toast) toast.textContent = `保存失败：${e.message}`;
  }
}

window.isSettingsViewActive = isSettingsViewActive;
window.uploadStgAvatar = uploadStgAvatar;
window.copyStgClawbotCli = copyStgClawbotCli;
window.copyStgBridgeStart = copyStgBridgeStart;
window.copyStgText = copyStgText;
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
window.saveStgWechatChannels = saveStgWechatChannels;
window.testStgWechatChannels = testStgWechatChannels;
window.saveStgFeishuChannels = saveStgFeishuChannels;
window.openStgSkillDrawer = openStgSkillDrawer;
window.closeStgSkillDrawer = closeStgSkillDrawer;
window.onStgSkillSearch = onStgSkillSearch;
window.saveStgSkillRoutes = saveStgSkillRoutes;
window.openStgChainEditor = openStgChainEditor;
window.cycleStgToolPolicy = cycleStgToolPolicy;
