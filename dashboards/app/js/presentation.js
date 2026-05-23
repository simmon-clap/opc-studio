/**
 * Presentation layer — renders versioned blocks from dashboard.presentation.*
 * Keep in sync with backend/app/presentation/schema.py
 */
const Presentation = (() => {
  const VERSION = 1;

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function inline(text) {
    return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function renderBlocks(blocks) {
    if (!blocks?.length) return "";
    return blocks.map((block) => {
      switch (block.type) {
        case "paragraph":
          return `<p class="pb-paragraph">${inline(block.text || "")}</p>`;
        case "heading":
          return `<div class="pb-heading pb-heading-${block.level || 2}">${inline(block.text || "")}</div>`;
        case "list":
          return `<ul class="pb-list">${(block.items || [])
            .map((item) => `<li>${inline(item)}</li>`)
            .join("")}</ul>`;
        case "callout":
          return `<div class="pb-callout tone-${block.tone || "info"}">${inline(block.text || "")}</div>`;
        case "task_row":
          return `<div class="pb-task-row">
            <span class="pb-task-role">${inline(block.role || "")}</span>
            <span class="pb-task-title">${inline(block.title || "")}</span>
            <span class="pb-task-status">${inline(block.status || "")}</span>
          </div>`;
        default:
          return block.text ? `<p>${inline(block.text)}</p>` : "";
      }
    }).join("");
  }

  /** Prefer structured content; fall back to markdown-lite plain text. */
  function renderMessageContent(msg) {
    const content = msg?.content;
    if (content?.version === VERSION && content.blocks?.length) {
      return renderBlocks(content.blocks);
    }
    return formatChatMessageLegacy(msg?.text || "");
  }

  function formatChatMessageLegacy(text) {
    if (!text) return "";
    const safe = escapeHtml(text);
    return safe
      .split(/\n{2,}/)
      .map((block) => {
        const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
        if (!lines.length) return "";
        const chunks = [];
        let listBuf = [];
        const flushList = () => {
          if (!listBuf.length) return;
          chunks.push(
            `<ul class="pb-list">${listBuf.map((l) => `<li>${inline(l.slice(2))}</li>`).join("")}</ul>`
          );
          listBuf = [];
        };
        for (const line of lines) {
          if (line.startsWith("- ")) {
            listBuf.push(line);
            continue;
          }
          flushList();
          if (/^\*\*.+\*\*$/.test(line)) {
            chunks.push(`<div class="pb-heading">${inline(line.replace(/^\*\*|\*\*$/g, ""))}</div>`);
          } else {
            chunks.push(`<p class="pb-paragraph">${inline(line)}</p>`);
          }
        }
        flushList();
        return chunks.join("");
      })
      .join("");
  }

  function getOverview(data) {
    return data?.presentation?.overview || data?.overviewLive || null;
  }

  function syncRoleLayout(data) {
    const roles = data?.presentation?.roles;
    if (!roles?.length || typeof ROLE_POS === "undefined") return;
    roles.forEach((r) => {
      if (r.id && r.overview) {
        ROLE_POS[r.id] = { x: r.overview.x, y: r.overview.y };
      }
    });
  }

  return {
    VERSION,
    renderBlocks,
    renderMessageContent,
    getOverview,
    syncRoleLayout,
  };
})();
